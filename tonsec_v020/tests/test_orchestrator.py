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
