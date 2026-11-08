import unittest

from tonsec.chain_audit import (
    validate_address,
    _conflicts,
    _observations,
    _endpoint_state,
    analyze_transactions,
    _correlate_messages,
)


class ChainAuditTests(unittest.TestCase):

    def test_accepts_raw_address(self):
        value = "0:" + ("a" * 64)
        self.assertEqual(validate_address(value), value)

    def test_accepts_friendly_address(self):
        value = "UQ" + ("A" * 46)
        self.assertEqual(validate_address(value), value)

    def test_rejects_invalid_address(self):
        with self.assertRaises(ValueError):
            validate_address("not-a-ton-address")

    def test_detects_provider_conflict(self):
        observations = [
            {
                "provider": "tonapi.account",
                "status": "active",
                "balance": "100",
                "is_wallet": True,
                "code_hash": "abc",
                "data_hash": None,
            },
            {
                "provider": "toncenter.walletStates",
                "status": "active",
                "balance": "100",
                "is_wallet": False,
                "code_hash": "abc",
                "data_hash": None,
            },
        ]

        conflicts = _conflicts(observations)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["field"], "is_wallet")
        self.assertEqual(
            conflicts[0]["classification"],
            "CONFLICTING_EVIDENCE",
        )

    def test_observations_preserve_provider_identity(self):
        data = {
            "tonapi": {
                "account": {
                    "ok": True,
                    "data": {
                        "address": "x",
                        "status": "active",
                        "is_wallet": True,
                        "interfaces": ["wallet_highload_v3r1"],
                    },
                }
            },
            "toncenter": {},
        }

        result = _observations(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["provider"], "tonapi.account")
        self.assertEqual(result[0]["interfaces"], ["wallet_highload_v3r1"])


    def test_numeric_balance_types_do_not_create_false_conflict(self):
        observations = [
            {"provider": "toncenter", "balance": "139164621438022"},
            {"provider": "tonapi", "balance": 139164621438022},
        ]
        self.assertEqual(_conflicts(observations), [])

    def test_http_429_is_rate_limited(self):
        self.assertEqual(
            _endpoint_state({"ok": False, "http_status": 429}),
            "RATE_LIMITED",
        )


    def test_exact_message_hash_correlation(self):
        records = [
            {"provider": "tonapi", "transaction": {
                "hash": "request",
                "out_msgs": [{"hash": "message-1"}],
            }},
            {"provider": "tonapi", "transaction": {
                "hash": "execution",
                "in_msg": {"hash": "message-1"},
            }},
        ]
        result = _correlate_messages(records)
        self.assertEqual(len(result["correlations"]), 1)
        self.assertEqual(
            result["correlations"][0]["evidence"],
            "EXACT_MESSAGE_HASH",
        )

    def test_unmatched_outgoing_message(self):
        records = [{
            "provider": "tonapi",
            "transaction": {
                "hash": "tx1",
                "out_msgs": [{"hash": "orphan"}],
            },
        }]
        result = _correlate_messages(records)
        self.assertEqual(result["correlations"], [])
        self.assertEqual(result["unmatched_outgoing"], ["orphan"])

    def test_duplicate_inbound_hash_is_not_correlated(self):
        records = [
            {"provider": "tonapi", "transaction": {
                "hash": "a", "out_msgs": [{"hash": "same"}],
            }},
            {"provider": "tonapi", "transaction": {
                "hash": "b", "in_msg": {"hash": "same"},
            }},
            {"provider": "tonapi", "transaction": {
                "hash": "c", "in_msg": {"hash": "same"},
            }},
        ]
        result = _correlate_messages(records)
        self.assertEqual(result["correlations"], [])
        self.assertIn("same", result["ambiguous_hashes"])

    def test_failed_transaction_is_reported_as_info(self):
        data = {"tonapi": {"transactions": {
            "ok": True,
            "data": {"transactions": [{
                "hash": "failed-tx",
                "success": False,
                "aborted": True,
                "compute_phase": {"success": False},
                "action_phase": {"success": False},
            }]},
        }}}
        result = analyze_transactions(data)
        self.assertEqual(result["status"], "ANALYZED")
        self.assertEqual(len(result["failed_transactions"]), 1)
        self.assertEqual(result["findings"][0]["severity"], "INFO")

    def test_unavailable_429_is_not_zero_transactions(self):
        data = {"toncenter": {"transactions": {
            "ok": False, "http_status": 429,
        }}}
        result = analyze_transactions(data)
        self.assertEqual(result["status"], "NO_TRANSACTION_DATA")
        self.assertIsNone(
            result["provider_collection"]["toncenter"]["record_count"]
        )
        self.assertEqual(
            result["provider_collection"]["toncenter"]["status"],
            "RATE_LIMITED",
        )


if __name__ == "__main__":
    unittest.main()
