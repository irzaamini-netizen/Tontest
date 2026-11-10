import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tonsec.engine import scan_source

class BenchmarkFixtureTests(unittest.TestCase):
    def test_no_guard_flags_auth(self):
        path = ROOT / "benchmark/fixtures/auth_no_guard.fc"
        findings, _ = scan_source(str(path), path.read_text())
        self.assertTrue(any(f["rule_id"] == "TON-AUTH-001" for f in findings))

if __name__ == "__main__":
    unittest.main()
