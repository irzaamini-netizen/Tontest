import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone


def scan_project(root, exclude_roots=None):
    from .engine import EXTS, SKIP, _analyze_source

    rp = Path(root).expanduser().resolve()
    if not rp.is_dir():
        raise ValueError(f"Not a directory: {rp}")

    excluded_roots = {
        Path(item).expanduser().resolve()
        for item in (exclude_roots or [])
    }

    if any(rp == item for item in excluded_roots):
        raise ValueError("Project root cannot exclude itself.")

    findings = []
    records = []
    skipped = {
        "unsupported": 0,
        "too_large": 0,
        "unreadable": 0,
    }

    for base, dirs, names in os.walk(rp):
        current = Path(base).resolve()
        dirs[:] = sorted(
            d for d in dirs
            if d not in SKIP
            and (current / d).resolve() not in excluded_roots
        )

        for name in sorted(names):
            file_path = Path(base) / name
            suffix = file_path.suffix.lower()

            if suffix not in EXTS:
                skipped["unsupported"] += 1
                continue

            try:
                if file_path.stat().st_size > 2 * 1024 * 1024:
                    skipped["too_large"] += 1
                    continue

                raw = file_path.read_bytes()
                decode_error = False

                try:
                    src = raw.decode("utf-8")
                except UnicodeDecodeError:
                    src = raw.decode("utf-8", errors="replace")
                    decode_error = True

                relative = str(file_path.relative_to(rp))

                file_findings, functions, diagnostics = _analyze_source(
                    relative, src
                )

                findings.extend(file_findings)

                parser_mode = (
                    "func_structural"
                    if suffix in {".fc", ".func"}
                    else "tolk_structural"
                    if suffix == ".tolk"
                    else "legacy_heuristic"
                )

                diagnostics = list(diagnostics)

                if decode_error:
                    diagnostics.append({
                        "code": "INPUT001",
                        "message": "Invalid UTF-8 detected; replacement decoding was used.",
                        "severity": "warning",
                        "line": 1,
                        "column": 1,
                        "offset": 0,
                    })

                notes = []

                if parser_mode == "legacy_heuristic":
                    notes.append(
                        "This file uses legacy heuristic function extraction."
                    )

                if decode_error:
                    notes.append(
                        "Source encoding was not valid UTF-8."
                    )

                status = (
                    "PARTIAL"
                    if diagnostics or notes
                    else "COMPLETE"
                )

                records.append({
                    "path": relative,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                    "language_parser": parser_mode,
                    "functions_extracted": len(functions),
                    "function_names": [fn.name for fn in functions],
                    "analysis_status": status,
                    "analysis_notes": notes,
                    "diagnostics": diagnostics,
                })

            except OSError:
                skipped["unreadable"] += 1

    all_diagnostics = [
        item
        for record in records
        for item in record["diagnostics"]
    ]

    partial_files = sum(
        record["analysis_status"] == "PARTIAL"
        for record in records
    )

    return {
        "schema": "tonsec.raw-report.v1",
        "engine": "TON Security Engine",
        "engine_version": "0.2.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target": str(rp),
        "mode": "READ_ONLY_STATIC_ANALYSIS",

        "analysis_pipeline": {
            "architecture": "CENTRAL_PIPELINE_V1",
            "stages": [
                {
                    "name": "source_discovery",
                    "status": "COMPLETE",
                },
                {
                    "name": "language_parsing",
                    "status": "PARTIAL" if partial_files else "COMPLETE",
                },
                {
                    "name": "security_rules",
                    "status": "HEURISTIC",
                },
                {
                    "name": "interprocedural_analysis",
                    "status": "NOT_IMPLEMENTED",
                },
                {
                    "name": "control_flow_analysis",
                    "status": "NOT_IMPLEMENTED",
                },
                {
                    "name": "data_flow_analysis",
                    "status": "NOT_IMPLEMENTED",
                },
                {
                    "name": "bytecode_analysis",
                    "status": "NOT_IMPLEMENTED",
                },
                {
                    "name": "result_aggregation",
                    "status": "COMPLETE",
                },
            ],
        },

        "summary": {
            "files_analyzed": len(records),
            "files_complete": len(records) - partial_files,
            "files_partial": partial_files,
            "functions_extracted": sum(
                item["functions_extracted"] for item in records
            ),
            "findings_total": len(findings),
            "files_with_diagnostics": sum(
                bool(item["diagnostics"]) for item in records
            ),
            "diagnostics_total": len(all_diagnostics),
            "diagnostics_by_severity": {
                severity: sum(
                    item["severity"] == severity
                    for item in all_diagnostics
                )
                for severity in ("error", "warning", "info")
            },
            "by_severity": {
                severity: sum(
                    item["severity"] == severity
                    for item in findings
                )
                for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
            },
            "skipped": skipped,
        },

        "files": records,
        "findings": findings,

        "coverage": {
            "rules": [
                "TON-AUTH-001",
                "TON-REPLAY-001",
                "TON-TIME-001",
                "TON-REPLAY-002",
                "TON-EXT-001",
                "TON-ASSET-001",
                "TON-ASSET-002",
                "TON-CLIENT-001",
            ],
            "limitations": [
                "FunC parser is an initial structural parser, not compiler-grade.",
                "Tact currently uses legacy heuristic extraction. Tolk uses an initial structural parser and is not yet compiler-grade.",
                "No interprocedural call graph or semantic type resolution.",
                "No control-flow or state/dataflow analysis.",
                "No TVM bytecode analysis.",
                "Security rules are heuristic and do not prove exploitability.",
                "Authorization in helpers, modifiers, and callers may be missed.",
                "Files with incomplete parsing or input decoding are marked PARTIAL.",
            ],
        },
    }
