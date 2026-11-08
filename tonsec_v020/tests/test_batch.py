import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tonsec.batch import discover_projects, audit_batch


class BatchTests(unittest.TestCase):

    def make_project(self, root, name):
        project = root / name
        project.mkdir()
        (project / "wallet.fc").write_text(
            "() withdraw() impure { send_raw_message(msg, 0); }",
            encoding="utf-8",
        )
        return project

    def test_discovers_immediate_projects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root, "alpha")
            self.make_project(root, "beta")
            found = discover_projects(root)
            self.assertEqual([p.name for p in found], ["alpha", "beta"])

    def test_collection_root_files_do_not_hide_child_projects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "loose-data.txt").write_text("sample", encoding="utf-8")
            self.make_project(root, "alpha")
            self.make_project(root, "beta")

            found = discover_projects(root)
            self.assertEqual([p.name for p in found], ["alpha", "beta"])

    def test_project_root_is_single_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root, "source")
            project = root / "source"
            self.assertEqual(discover_projects(project), [project.resolve()])

    def test_batch_creates_aggregate_and_individual_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "collection"
            root.mkdir()
            self.make_project(root, "alpha")
            self.make_project(root, "beta")
            output = Path(temp) / "result"

            report = audit_batch(root, output)

            self.assertEqual(report["summary"]["total_projects"], 2)
            self.assertEqual(report["summary"]["projects_succeeded"], 2)
            self.assertTrue((output / "batch_report.json").is_file())
            self.assertTrue((output / "batch_report.md").is_file())
            self.assertEqual(
                len(list((output / "projects").glob("*/ton_raw.json"))),
                2,
            )

    def test_failure_does_not_stop_remaining_projects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "collection"
            root.mkdir()
            self.make_project(root, "alpha")
            self.make_project(root, "beta")
            output = Path(temp) / "result"

            from tonsec import batch
            original = batch.scan_project

            def controlled(project, **kwargs):
                if Path(project).name == "alpha":
                    raise RuntimeError("controlled test failure")
                return original(project, **kwargs)

            with patch("tonsec.batch.scan_project", side_effect=controlled):
                report = audit_batch(root, output)

            self.assertEqual(report["summary"]["projects_failed"], 1)
            self.assertEqual(report["summary"]["projects_succeeded"], 1)
            self.assertEqual(
                [p["status"] for p in report["projects"]],
                ["FAILED", "SUCCESS"],
            )

    def test_nonempty_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "collection"
            root.mkdir()
            self.make_project(root, "alpha")
            output = Path(temp) / "result"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("keep")

            with self.assertRaises(FileExistsError):
                audit_batch(root, output)

            self.assertEqual(marker.read_text(), "keep")

    def test_output_inside_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "collection"
            root.mkdir()
            self.make_project(root, "alpha")
            with self.assertRaises(ValueError):
                audit_batch(root, root / "reports")


class TestRecursiveTonProjectDiscovery(unittest.TestCase):
    def test_discovers_nested_mutation_projects_without_parent_duplicate(self):
        import tempfile
        from pathlib import Path
        from tonsec.batch import discover_projects

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("baseline", "M01", "M02"):
                contract = root / "mut" / name / "contracts"
                contract.mkdir(parents=True)
                (contract / "wallet.tolk").write_text("contract", encoding="utf-8")

            result = discover_projects(root / "mut")
            self.assertEqual(
                {p.name for p in result},
                {"baseline", "M01", "M02"}
            )
            self.assertEqual(len(result), 3)

    def test_ignores_generic_text_directories(self):
        import tempfile
        from pathlib import Path
        from tonsec.batch import discover_projects

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "gitleaks").mkdir()
            (root / "gitleaks" / "README.txt").write_text("text", encoding="utf-8")
            (root / "secret-test").mkdir()
            (root / "secret-test" / "sample.txt").write_text("text", encoding="utf-8")
            with self.assertRaises(ValueError):
                discover_projects(root)

    def test_child_projects_are_not_hidden_by_root_files(self):
        import tempfile
        from pathlib import Path
        from tonsec.batch import discover_projects

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.txt").write_text("collection", encoding="utf-8")
            for name in ("project-a", "project-b"):
                contract = root / name / "contracts"
                contract.mkdir(parents=True)
                (contract / "main.fc").write_text("contract", encoding="utf-8")

            result = discover_projects(root)
            self.assertEqual(
                {p.name for p in result},
                {"project-a", "project-b"}
            )

    def test_single_project_root_fallback(self):
        import tempfile
        from pathlib import Path
        from tonsec.batch import discover_projects

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "contracts"
            contract.mkdir()
            (contract / "main.tolk").write_text("contract", encoding="utf-8")
            self.assertEqual(discover_projects(root), [root.resolve()])


    def test_discovers_nested_project_inside_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "parent"
            child = parent / "tools" / "child"

            parent_contracts = parent / "contracts"
            child_contracts = child / "contracts"

            parent_contracts.mkdir(parents=True)
            child_contracts.mkdir(parents=True)

            (parent_contracts / "main.tolk").write_text(
                "contract Parent {}",
                encoding="utf-8",
            )
            (child_contracts / "child.fc").write_text(
                "() main() { return (); }",
                encoding="utf-8",
            )

            found = discover_projects(root)

            self.assertEqual(
                set(found),
                {parent.resolve(), child.resolve()},
            )

    def test_discovers_func_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "func-project"
            contracts = project / "contracts"
            contracts.mkdir(parents=True)

            (contracts / "wallet.func").write_text(
                "source",
                encoding="utf-8",
            )

            self.assertEqual(
                discover_projects(root),
                [project.resolve()],
            )

    def test_nested_project_files_are_not_scanned_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "collection"
            parent = root / "parent"
            child = parent / "tools" / "child"

            (parent / "contracts").mkdir(parents=True)
            (child / "contracts").mkdir(parents=True)

            (parent / "contracts" / "main.tolk").write_text(
                "contract Parent {}",
                encoding="utf-8",
            )
            (child / "contracts" / "child.fc").write_text(
                "() main() { return (); }",
                encoding="utf-8",
            )

            output = Path(tmp) / "reports"
            report = audit_batch(root, output)

            self.assertEqual(report["summary"]["total_projects"], 2)
            self.assertEqual(report["summary"]["projects_succeeded"], 2)

            raw_reports = sorted(
                (output / "projects").glob("*/ton_raw.json")
            )
            self.assertEqual(len(raw_reports), 2)

            scanned_paths = []
            for report_path in raw_reports:
                raw = json.loads(report_path.read_text(encoding="utf-8"))
                scanned_paths.extend(
                    (raw["target"], item["path"])
                    for item in raw["files"]
                )

            self.assertEqual(len(scanned_paths), 2)
            self.assertEqual(
                {Path(target).resolve() for target, _ in scanned_paths},
                {parent.resolve(), child.resolve()},
            )
            self.assertEqual(
                {path for _, path in scanned_paths},
                {"contracts/main.tolk", "contracts/child.fc"},
            )


if __name__ == "__main__":
    unittest.main()
