import json
import tempfile
import unittest
from pathlib import Path

from tonsec.orchestrator import run_collection


class UnifiedRunTests(unittest.TestCase):
    def test_run_creates_aggregate_reports_and_marks_chain_stage_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "collection"
            project = root / "alpha" / "contracts"
            project.mkdir(parents=True)
            (project / "wallet.tolk").write_text(
                "fun main() { return; }", encoding="utf-8"
            )
            output = Path(tmp) / "reports"

            report = run_collection(root, output)

            self.assertEqual(report["summary"]["total_projects"], 1)
            self.assertEqual(report["summary"]["project_reports_read"], 1)
            self.assertEqual(
                report["stages"][3]["status"],
                "NOT_RUN_REQUIRES_USER_APPROVED_WALLET",
            )
            self.assertTrue((output / "full_report.json").is_file())
            self.assertTrue((output / "full_report.md").is_file())

            saved = json.loads(
                (output / "full_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["schema"], "tonsec.unified-report.v1")
            self.assertEqual(saved["summary"]["files_analyzed"], 1)


if __name__ == "__main__":
    unittest.main()

    def test_missing_project_report_marks_aggregation_partial(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            root.mkdir()
            output = Path(tmp) / "reports"
            output.mkdir()

            fake_batch = {
                "output_dir": str(output),
                "input": str(root),
                "summary": {
                    "total_projects": 1,
                    "files_analyzed": 1,
                    "findings_total": 0,
                    "functions_extracted": 1,
                    "projects_succeeded": 1,
                    "projects_failed": 0,
                    "projects_partial": 0,
                },
                "projects": [{
                    "name": "alpha",
                    "path": str(root / "alpha"),
                    "status": "SUCCESS",
                    "report_dir": str(output / "missing-project-report"),
                }],
            }

            with patch(
                "tonsec.orchestrator.audit_batch",
                return_value=fake_batch,
            ):
                report = run_collection(root, output)

            statuses = {
                item["name"]: item["status"]
                for item in report["stages"]
            }
            self.assertEqual(statuses["report_aggregation"], "PARTIAL")
            self.assertEqual(statuses["static_source_analysis"], "PARTIAL")
            self.assertEqual(report["summary"]["project_reports_expected"], 1)
            self.assertEqual(report["summary"]["project_reports_read"], 0)
            self.assertEqual(report["summary"]["project_reports_missing"], 1)
            self.assertEqual(
                report["projects"][0]["aggregation_status"],
                "MISSING",
            )
            self.assertEqual(len(report["aggregation_errors"]), 1)

