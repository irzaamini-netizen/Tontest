"""Regression tests for evidence-based AUTH/REPLAY/TIME guards."""
import unittest
from tonsec.engine import has_auth_guard, scan_source
from tonsec.pipeline import scan_project
from pathlib import Path
import tempfile


class AuthRegressionTests(unittest.TestCase):
    def test_equal_slices_owner_is_guard(self):
        src = """
() withdraw() impure {
  throw_unless(100, equal_slices(sender_address, owner_address));
  send_raw_message(msg, 0);
}
"""
        rules = [f["rule_id"] for f in scan_source("w.fc", src)[0]]
        self.assertNotIn("TON-AUTH-001", rules)

    def test_equal_slices_without_role_not_guard(self):
        src = """
() withdraw() impure {
  throw_unless(100, equal_slices(a, b));
  send_raw_message(msg, 0);
}
"""
        rules = [f["rule_id"] for f in scan_source("w.fc", src)[0]]
        self.assertIn("TON-AUTH-001", rules)

    def test_slice_data_equal_wallet_is_guard(self):
        self.assertTrue(
            has_auth_guard("if (slice_data_equal?(s_addr, wallet)) { return (); }")
        )

    def test_tolk_camel_case_owner_address(self):
        src = """
fun withdraw() {
  assert(in.senderAddress == storage.ownerAddress);
  send(msg);
}
"""
        rules = [f["rule_id"] for f in scan_source("w.tolk", src)[0]]
        self.assertNotIn("TON-AUTH-001", rules)

    def test_royalty_helper_not_flagged(self):
        src = """
() send_royalty_params(slice to_address, int query_id, slice data) impure inline {
  var msg = begin_cell().store_slice(to_address).store_slice(data);
  send_raw_message(msg.end_cell(), 64);
}
"""
        rules = [f["rule_id"] for f in scan_source("c.fc", src)[0]]
        self.assertNotIn("TON-AUTH-001", rules)

    def test_unprotected_send_still_flagged(self):
        src = """
() withdraw() impure {
  send_raw_message(msg, 0);
}
"""
        rules = [f["rule_id"] for f in scan_source("w.fc", src)[0]]
        self.assertIn("TON-AUTH-001", rules)

    def test_seqno_with_compare_not_replay002(self):
        src = """
() recv_external(slice in_msg) impure {
  int msg_seqno = in_msg~load_uint(32);
  throw_unless(33, msg_seqno == stored_seqno);
  accept_message();
}
"""
        rules = [f["rule_id"] for f in scan_source("w.fc", src)[0]]
        self.assertNotIn("TON-REPLAY-002", rules)

    def test_tact_parser_extracts_handlers(self):
        from tonsec.tact_parser import parse_tact
        src = """
contract Demo {
  receive(msg: Transfer) { return (); }
  external(msg: Ext) { return (); }
  get fun balance(): Int { return 0; }
  fun helper() { return (); }
}
"""
        names = [f.name for f in parse_tact(src).functions]
        self.assertEqual(set(names), {"receive", "external", "balance", "helper"})

    def test_pipeline_marks_tact_structural(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Demo.tact"
            p.write_text("contract D { fun f() { return (); } }\n", encoding="utf-8")
            report = scan_project(d)
            self.assertEqual(report["files"][0]["language_parser"], "tact_structural")


if __name__ == "__main__":
    unittest.main()
