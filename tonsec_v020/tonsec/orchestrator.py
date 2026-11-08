import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .batch import audit_batch


LANGUAGES = {
    ".fc": "FunC",
    ".func": "FunC",
    ".tolk": "Tolk",
    ".tact": "Tact",
    ".ts": "TypeScript",
    ".js": "JavaScript",
    ".py": "Python",
}


def run_collection(root, outdir):
    batch = audit_batch(root, outdir)
    output = Path(batch["output_dir"])

    languages = Counter()
    parsers = Counter()
    file_states = Counter()
    severities = Counter()
    rules = Counter()
    project_reports = 0
    expected_reports = 0
    missing_reports = 0
    findings_total = 0
    diagnostics_total = 0
    aggregation_errors = []

    for project in batch["projects"]:
        if project.get("status") == "FAILED":
            project["aggregation_status"] = "NOT_AVAILABLE_PROJECT_FAILED"
            continue

        expected_reports += 1
        report_dir = project.get("report_dir")
        if not report_dir:
            error = "Project has no report_dir."
            project["aggregation_status"] = "MISSING"
            project["aggregation_error"] = error
            missing_reports += 1
            aggregation_errors.append({
                "project": project.get("name", "UNKNOWN"),
                "error": error,
            })
            continue

        raw_path = Path(report_dir) / "ton_raw.json"
        if not raw_path.is_file():
            error = "ton_raw.json does not exist."
            project["aggregation_status"] = "MISSING"
            project["aggregation_error"] = error
            missing_reports += 1
            aggregation_errors.append({
                "project": project.get("name", "UNKNOWN"),
                "error": error,
            })
            continue

        try:
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Report root is not an object.")
            if raw.get("schema") != "tonsec.raw-report.v1":
                raise ValueError("Unexpected or missing report schema.")
            if not isinstance(raw.get("findings"), list):
                raise ValueError("Report findings field is not a list.")
            if not isinstance(raw.get("files"), list):
                raise ValueError("Report files field is not a list.")
        except (OSError, ValueError, TypeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            project["aggregation_status"] = "INVALID"
            project["aggregation_error"] = error
            missing_reports += 1
            aggregation_errors.append({
                "project": project.get("name", "UNKNOWN"),
                "error": error,
            })
            continue

        project["aggregation_status"] = "READ"
        project_reports += 1

        findings = raw["findings"]
        findings_total += len(findings)

        for finding in findings:
            if not isinstance(finding, dict):
                continue
            severities[str(finding.get("severity", "UNKNOWN"))] += 1
            rules[str(finding.get("rule_id", "UNKNOWN"))] += 1

        for record in raw["files"]:
            if not isinstance(record, dict):
                continue
            suffix = Path(record.get("path", "")).suffix.lower()
            languages[LANGUAGES.get(suffix, "Other")] += 1
            parsers[str(record.get("language_parser", "UNKNOWN"))] += 1
            file_states[str(record.get("analysis_status", "UNKNOWN"))] += 1
            diagnostics_total += len(record.get("diagnostics", []))

    aggregation_partial = missing_reports > 0
    source_partial = (
        bool(batch["summary"]["projects_failed"])
        or bool(batch["summary"]["projects_partial"])
        or aggregation_partial
    )

    summary = {
        **batch["summary"],
        "project_reports_expected": expected_reports,
        "project_reports_read": project_reports,
        "project_reports_missing": missing_reports,
        "source_files_by_language": dict(sorted(languages.items())),
        "files_by_parser": dict(sorted(parsers.items())),
        "files_by_analysis_status": dict(sorted(file_states.items())),
        "findings_by_severity": dict(sorted(severities.items())),
        "findings_by_rule": dict(sorted(rules.items())),
        "findings_total_from_project_reports": findings_total,
        "diagnostics_total_from_project_reports": diagnostics_total,
    }

    stages = [
        {"name": "project_discovery", "status": "COMPLETE"},
        {
            "name": "static_source_analysis",
            "status": "PARTIAL" if source_partial else "COMPLETE",
        },
        {
            "name": "report_aggregation",
            "status": "PARTIAL" if aggregation_partial else "COMPLETE",
        },
        {
            "name": "on_chain_collection",
            "status": "NOT_RUN_REQUIRES_USER_APPROVED_WALLET",
        },
        {"name": "interprocedural_analysis", "status": "NOT_IMPLEMENTED"},
        {"name": "control_flow_analysis", "status": "NOT_IMPLEMENTED"},
        {"name": "data_flow_analysis", "status": "NOT_IMPLEMENTED"},
        {"name": "tvm_bytecode_analysis", "status": "NOT_IMPLEMENTED"},
    ]

    report = {
        "schema": "tonsec.unified-report.v1",
        "engine": "TON Security Engine",
        "engine_version": "0.2.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_UNIFIED_SOURCE_AUDIT",
        "input": batch["input"],
        "output_dir": str(output),
        "summary": summary,
        "stages": stages,
        "projects": batch["projects"],
        "aggregation_errors": aggregation_errors,
        "limitations": [
            "This command performs read-only source analysis; it does not submit transactions or sign messages.",
            "On-chain collection is not run by this command.",
            "FunC and Tolk parsers are initial structural parsers, not compiler-grade.",
            "Tact and several other source types use heuristic extraction.",
            "Interprocedural, control-flow, data-flow and TVM bytecode analysis are not implemented.",
            "Heuristic findings do not prove exploitability.",
            "A failed, partial, missing or invalid project report is not represented as a complete audit.",
        ],
    }

    (output / "full_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# TON Security Engine — Unified Report",
        f"- Input: `{report['input']}`",
        f"- Projects discovered: {summary['total_projects']}",
        f"- Succeeded: {summary['projects_succeeded']}",
        f"- Partial: {summary['projects_partial']}",
        f"- Failed: {summary['projects_failed']}",
        f"- Project reports expected: {expected_reports}",
        f"- Project reports read: {project_reports}",
        f"- Project reports missing/invalid: {missing_reports}",
        f"- Source files analyzed: {summary['files_analyzed']}",
        f"- Findings: {findings_total}",
        f"- Diagnostics: {diagnostics_total}",
        "",
        "## Source language coverage",
    ]
    lines.extend(
        f"- {name}: {count}" for name, count in sorted(languages.items())
    )
    lines += ["", "## Findings by severity"]
    lines.extend(
        f"- {name}: {count}" for name, count in sorted(severities.items())
    )
    lines += ["", "## Pipeline stages"]
    lines.extend(
        f"- {stage['name']}: {stage['status']}" for stage in stages
    )
    lines += ["", "## Aggregation errors"]
    if aggregation_errors:
        lines.extend(
            f"- {item['project']}: {item['error']}"
            for item in aggregation_errors
        )
    else:
        lines.append("- None")
    lines += ["", "## Limitations"]
    lines.extend("- " + item for item in report["limitations"])
    (output / "full_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return report
