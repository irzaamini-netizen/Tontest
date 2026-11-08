import json
import os
from pathlib import Path
from datetime import datetime, timezone

from .engine import EXTS, SKIP, write_report
from .pipeline import scan_project


def _has_source_files(root, recursive=True):
    root = Path(root)

    if not recursive:
        return any(
            item.is_file() and item.suffix.lower() in EXTS
            for item in root.iterdir()
        )

    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        if any(Path(name).suffix.lower() in EXTS for name in names):
            return True
    return False


def discover_projects(root):
    """
    Discover parent and nested TON projects.

    Conventional source directories are not projects by themselves,
    but their child directories are still traversed to find nested
    projects. Nested project roots are returned separately.
    """
    import os
    from pathlib import Path

    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project collection is not a directory: {root}")

    ignored = set(SKIP) | {
        ".acton", ".git", ".github", ".venv", "venv",
        "node_modules", "__pycache__", "dist", "build"
    }
    extensions = {".fc", ".func", ".tolk", ".tact"}
    source_roots = {"contracts", "contract", "sources", "src"}

    def child_directories(directory):
        try:
            return sorted(
                p for p in directory.iterdir()
                if p.is_dir()
                and p.name not in ignored
                and not p.name.startswith(".")
            )
        except OSError:
            return []

    def has_sources(directory):
        if not directory.is_dir():
            return False

        for current, dirs, files in os.walk(directory):
            dirs[:] = sorted(
                d for d in dirs
                if d not in ignored and not d.startswith(".")
            )
            if any(
                Path(name).suffix.lower() in extensions
                for name in files
            ):
                return True
        return False

    def is_project(directory):
        try:
            if any(
                p.is_file() and p.suffix.lower() in extensions
                for p in directory.iterdir()
            ):
                return True
        except OSError:
            return False

        return any(
            has_sources(directory / name)
            for name in source_roots
        )

    found = []

    def descend(directory):
        directory = Path(directory)

        # Source directories are not standalone projects.
        # Their children must still be inspected for nested projects.
        if is_project(directory):
            found.append(directory.resolve())

        for child in child_directories(directory):
            descend(child)

    for child in child_directories(root):
        descend(child)

    # The input itself can also be a project, even when it contains
    # nested projects. Keep both roots in that case.
    if is_project(root):
        found.append(root)

    found = sorted(set(found), key=lambda p: str(p))

    if not found:
        raise ValueError(f"No TON source projects found under: {root}")

    return found


def audit_batch(root, outdir):
    root = Path(root).expanduser().resolve()
    output = Path(outdir).expanduser().resolve()

    projects = discover_projects(root)

    if output == root or root in output.parents:
        raise ValueError("Output directory must not be inside the input directory.")

    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError(
            f"Refusing to overwrite non-empty output: {output}"
        )

    output.mkdir(parents=True, exist_ok=True)
    project_output = output / "projects"
    project_output.mkdir()

    results = []
    totals = {
        "files_analyzed": 0,
        "findings_total": 0,
        "functions_extracted": 0,
        "projects_succeeded": 0,
        "projects_failed": 0,
        "projects_partial": 0,
    }

    for index, project in enumerate(projects, 1):
        name = f"{index:04d}-{project.name}"
        record = {
            "name": project.name,
            "path": str(project),
            "status": "FAILED",
        }

        try:
            nested_projects = [
                candidate
                for candidate in projects
                if project in candidate.parents
            ]
            report = scan_project(
                project,
                exclude_roots=nested_projects,
            )
            destination = project_output / name
            write_report(report, str(destination))

            summary = report["summary"]
            record.update({
                "status": (
                    "PARTIAL"
                    if summary["files_partial"] > 0
                    or summary["skipped"]["unreadable"] > 0
                    else "SUCCESS"
                ),
                "report_dir": str(destination),
                "files_analyzed": summary["files_analyzed"],
                "findings_total": summary["findings_total"],
                "functions_extracted": summary["functions_extracted"],
                "skipped": summary["skipped"],
            })

            totals["files_analyzed"] += summary["files_analyzed"]
            totals["findings_total"] += summary["findings_total"]
            totals["functions_extracted"] += summary["functions_extracted"]

            if record["status"] == "SUCCESS":
                totals["projects_succeeded"] += 1
            else:
                totals["projects_partial"] += 1

        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            totals["projects_failed"] += 1

        results.append(record)

    batch_report = {
        "schema": "tonsec.batch-report.v1",
        "engine": "TON Security Engine",
        "engine_version": "0.2.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_STATIC_BATCH_ANALYSIS",
        "input": str(root),
        "summary": {
            "total_projects": len(projects),
            **totals,
        },
        "projects": results,
        "limitations": [
            "Discovery recursively checks eligible child directories and uses the input directory itself as a fallback project root.",
            "Static heuristic findings do not prove exploitability.",
            "A failed project does not stop the remaining projects.",
            "This batch command performs source scanning, not on-chain wallet auditing.",
        ],
    }

    json_path = output / "batch_report.json"
    json_path.write_text(
        json.dumps(batch_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# TON Security Engine — Batch Report",
        f"- Input: `{root}`",
        f"- Projects: {len(projects)}",
        f"- Succeeded: {totals['projects_succeeded']}",
        f"- Partial: {totals['projects_partial']}",
        f"- Failed: {totals['projects_failed']}",
        f"- Files analyzed: {totals['files_analyzed']}",
        f"- Findings: {totals['findings_total']}",
        "",
        "## Projects",
    ]

    for item in results:
        lines.append(
            f"- **{item['status']}** — `{item['name']}`: "
            f"{item.get('files_analyzed', 0)} files, "
            f"{item.get('findings_total', 0)} findings"
        )
        if "error" in item:
            lines.append(f"  - Error: {item['error']}")

    lines += ["", "## Limitations"]
    lines.extend("- " + item for item in batch_report["limitations"])

    (output / "batch_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    batch_report["output_dir"] = str(output)
    return batch_report
