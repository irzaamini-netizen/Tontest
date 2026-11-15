#!/usr/bin/env python3
"""
Prepare a local baseline dataset of real TON projects for evaluation.

This script is intentionally conservative:
- Clones only the repositories listed in real_projects.json
- Uses shallow clones
- Does not modify any project source
- Writes a manifest with clone status, commit SHA and basic file counts

Usage:
    python -m tonsec_v020.benchmark.tools.prepare_dataset \
        --dataset tonsec_v020/benchmark/datasets/real_projects.json \
        --outdir ~/tonsec-baseline-projects \
        [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
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


def clone_project(entry: dict, outdir: Path) -> dict:
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
    parser = argparse.ArgumentParser(description="Prepare real TON projects dataset")
    parser.add_argument("--dataset", required=True, help="Path to real_projects.json")
    parser.add_argument("--outdir", required=True, help="Directory to place clones")
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of projects")
    args = parser.parse_args()

    dataset_path = Path(args.dataset).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    projects = data.get("projects", [])
    if args.limit > 0:
        projects = projects[: args.limit]

    outdir.mkdir(parents=True, exist_ok=True)

    results = []
    for entry in projects:
        print(f"Preparing {entry['name']} ...", flush=True)
        results.append(clone_project(entry, outdir))

    manifest = {
        "schema": "tonsec.baseline-manifest.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path),
        "outdir": str(outdir),
        "summary": {
            "total": len(results),
            "cloned": sum(1 for r in results if r["status"] == "CLONED"),
            "already_present": sum(1 for r in results if r["status"] == "ALREADY_PRESENT"),
            "failed": sum(1 for r in results if r["status"] == "FAILED"),
        },
        "projects": results,
    }

    manifest_path = outdir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(manifest["summary"], indent=2))
    print(f"Manifest written to {manifest_path}")
    return 0 if manifest["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
