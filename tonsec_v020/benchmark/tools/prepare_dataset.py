#!/usr/bin/env python3
"""
Prepare a local baseline dataset of real TON projects for evaluation.

This script is intentionally conservative:
- Clones only the repositories listed in real_projects.json
- Uses shallow clones
- Does not modify any project source
- Writes a manifest with clone status, commit SHA and basic file counts

Usage:
    python tonsec_v020/benchmark/tools/prepare_dataset.py \
        --dataset tonsec_v020/benchmark/datasets/real_projects.json \
        --outdir ~/tonsec-baseline-projects \
        [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


EXTS = {".fc", ".func", ".tolk", ".tact"}


def run(cmd, cwd=None):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def count_sources(root: Path) -> dict:
    counts = {ext: 0 for ext in EXTS}
    total = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in EXTS:
            counts[suffix] += 1
            total += 1
    return {"by_extension": counts, "total_source_files": total}


def clone_project(entry: dict, outdir: Path, dry_run: bool = False) -> dict:
    name = entry["name"]
    url = entry["url"]
    target = outdir / name

    record = {
        "name": name,
        "url": url,
        "path": str(target),
        "status": "FAILED",
        "category": entry.get("category"),
        "languages": entry.get("languages", []),
    }

    if target.exists():
        code, stdout, stderr = run(["git", "-C", str(target), "rev-parse", "HEAD"])
        if code == 0:
            record["status"] = "ALREADY_PRESENT"
            record["commit"] = stdout
            record["sources"] = count_sources(target)
            return record
        record["error"] = (
            f"Path exists but is not a valid git repository: {target}"
        )
        return record

    if dry_run:
        record["status"] = "DRY_RUN_WOULD_CLONE"
        return record

    code, stdout, stderr = run(
        ["git", "clone", "--depth", "1", url, str(target)]
    )
    if code != 0:
        record["error"] = stderr or stdout or f"git clone failed with code {code}"
        return record

    code, stdout, stderr = run(["git", "-C", str(target), "rev-parse", "HEAD"])
    record["commit"] = stdout if code == 0 else None
    record["status"] = "CLONED"
    record["sources"] = count_sources(target)
    return record


def main():
    parser = argparse.ArgumentParser(
        description="Prepare real TON projects dataset for baseline evaluation"
    )
    parser.add_argument("--dataset", required=True, help="Path to real_projects.json")
    parser.add_argument("--outdir", required=True, help="Directory to place clones")
    parser.add_argument(
        "--limit", type=int, default=0, help="Optional max number of projects"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cloned without writing anything",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset).expanduser().resolve()
    if not dataset_path.is_file():
        print(f"ERROR: dataset file not found: {dataset_path}", file=sys.stderr)
        return 2

    outdir = Path(args.outdir).expanduser().resolve()

    try:
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot read dataset: {exc}", file=sys.stderr)
        return 2

    projects = data.get("projects", [])
    if not isinstance(projects, list) or not projects:
        print("ERROR: dataset contains no projects", file=sys.stderr)
        return 2

    if args.limit > 0:
        projects = projects[: args.limit]

    if not args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)

    results = []
    for entry in projects:
        if not isinstance(entry, dict) or "name" not in entry or "url" not in entry:
            results.append({
                "name": str(entry.get("name", "UNKNOWN")),
                "status": "FAILED",
                "error": "Invalid project entry in dataset",
            })
            continue

        print(f"Preparing {entry['name']} ...", flush=True)
        results.append(clone_project(entry, outdir, dry_run=args.dry_run))

    summary = {
        "total": len(results),
        "cloned": sum(1 for r in results if r["status"] == "CLONED"),
        "already_present": sum(1 for r in results if r["status"] == "ALREADY_PRESENT"),
        "dry_run": sum(1 for r in results if r["status"] == "DRY_RUN_WOULD_CLONE"),
        "failed": sum(1 for r in results if r["status"] == "FAILED"),
    }

    manifest = {
        "schema": "tonsec.baseline-manifest.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path),
        "outdir": str(outdir),
        "dry_run": bool(args.dry_run),
        "summary": summary,
        "projects": results,
    }

    if not args.dry_run:
        manifest_path = outdir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Manifest written to {manifest_path}")

    print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
