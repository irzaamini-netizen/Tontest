import unittest

from tonsec.engine import scan_source


class FuncEngineIntegrationTests(unittest.TestCase):
    def test_fc_unprotected_send_is_detected(self):
        source = "() withdraw() impure { send_raw_message(msg, 0); }"
        findings, functions = scan_source("wallet.fc", source)

        self.assertEqual([f.name for f in functions], ["withdraw"])
        self.assertIn("TON-AUTH-001", [f["rule_id"] for f in findings])

    def test_fc_authorization_guard_before_send_is_recognized(self):
        source = (
            "() withdraw() impure { "
            "throw_unless(401, sender() == owner); "
            "send_raw_message(msg, 0); }"
        )
        findings, _ = scan_source("wallet.fc", source)

        self.assertNotIn("TON-AUTH-001", [f["rule_id"] for f in findings])

    def test_func_extension_uses_func_parser(self):
        source = "() main() impure { send_raw_message(msg, 0); }"
        findings, functions = scan_source("wallet.func", source)

        self.assertEqual([f.name for f in functions], ["main"])
        self.assertIn("TON-AUTH-001", [f["rule_id"] for f in findings])

    def test_func_line_number_is_preserved(self):
        source = "\n() withdraw() impure { send_raw_message(msg, 0); }"
        findings, _ = scan_source("wallet.fc", source)

        auth = [f for f in findings if f["rule_id"] == "TON-AUTH-001"]
        self.assertEqual(len(auth), 1)
        self.assertEqual(auth[0]["line"], 2)

    def test_tolk_still_uses_legacy_parser(self):
        source = "fun withdraw(){ send_raw_message(msg, 0); }"
        findings, functions = scan_source("wallet.tolk", source)

        self.assertEqual([f.name for f in functions], ["withdraw"])
        self.assertIn("TON-AUTH-001", [f["rule_id"] for f in findings])


if __name__ == "__main__":
    unittest.main()
