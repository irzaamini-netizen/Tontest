import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tonsec.chain_audit import (
    validate_address,
    _conflicts,
    _observations,
    _endpoint_state,
    analyze_transactions,
    _correlate_messages,
    audit_wallet,
    write_chain_report,
)


class ChainAuditTests(unittest.TestCase):


    def test_partial_pagination_survives_final_report(self):
        pagination = {
            "enabled": True,
            "complete": False,
            "pages_fetched": 2,
            "page_size": 1000,
            "max_pages": 2,
            "next_offset": 2000,
            "fetched_count": 2000,
            "returned_count": 1998,
            "duplicate_count": 2,
            "stop_reason": "MAX_PAGES_REACHED",
            "snapshot_stable": False,
            "consistency": "OFFSET_BASED_NON_SNAPSHOT",
            "min_interval": 1.1,
        }
        collected = {
            "transactions": {
                "ok": True,
                "http_status": 200,
                "partial": True,
                "data": {"transactions": [{"hash": "fixture-tx"}]},
                "pagination": pagination,
            }
        }

        with patch("tonsec.chain_audit.ToncenterProvider") as center:
            center.return_value.collect.return_value = collected
            report = audit_wallet("0:" + ("a" * 64))

        self.assertEqual(report["collection"]["status"], "PARTIAL")
        endpoint = report["collection"]["endpoint_summary"]
        self.assertEqual(
            endpoint["toncenter"]["transactions"]["pagination"],
            pagination,
        )
        self.assertEqual(
            report["transaction_analysis"]["provider_collection"]
            ["toncenter"]["status"],
            "PARTIAL_RECORDS_RETURNED",
        )

        with tempfile.TemporaryDirectory() as outdir:
            write_chain_report(report, outdir)
            markdown = (
                Path(outdir) / "chain_audit.md"
            ).read_text(encoding="utf-8")

        self.assertIn("- Pagination complete: False", markdown)
        self.assertIn(
            "- Pagination stop reason: MAX_PAGES_REACHED", markdown
        )
        self.assertIn(
            "- Pagination consistency: OFFSET_BASED_NON_SNAPSHOT",
            markdown,
        )
        self.assertIn("PARTIAL_RECORDS_RETURNED", markdown)

    def test_default_audit_disables_tonapi(self):
        collected = {"transactions": {
            "ok": True,
            "data": {"transactions": []},
        }}
        with patch("tonsec.chain_audit.ToncenterProvider") as center:
            with patch("tonsec.chain_audit.TonapiProvider") as api:
                center.return_value.collect.return_value = collected
                report = audit_wallet("0:" + ("a" * 64))

        api.assert_not_called()
        center.return_value.collect.assert_called_once()
        self.assertEqual(report["collection"]["providers"], ["toncenter"])
        self.assertIsNone(report["activity"]["transaction_counts"]["tonapi"])
        self.assertEqual(
            report["activity"]["transaction_collection_status"]["tonapi"],
            "DISABLED",
        )
        self.assertEqual(report["collection"]["total_endpoints"], 1)

    def test_explicit_flag_enables_tonapi(self):
        collected = {"transactions": {
            "ok": True,
            "data": {"transactions": [{"hash": "fixture-tx"}]},
        }}
        with patch("tonsec.chain_audit.ToncenterProvider") as center:
            with patch("tonsec.chain_audit.TonapiProvider") as api:
                center.return_value.collect.return_value = collected
                api.return_value.collect.return_value = collected
                report = audit_wallet(
                    "0:" + ("a" * 64), enable_tonapi=True
                )

        api.assert_called_once_with()
        api.return_value.collect.assert_called_once()
        self.assertEqual(
            report["collection"]["providers"], ["toncenter", "tonapi"]
        )
        self.assertEqual(report["collection"]["total_endpoints"], 2)
        self.assertEqual(
            report["activity"]["transaction_collection_status"]["tonapi"],
            "RECORDS_RETURNED",
        )

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


class ToncenterPaginationTests(unittest.TestCase):

    @staticmethod
    def page(items):
        return {"ok": True, "http_status": 200,
                "data": {"transactions": items}}

    def provider(self):
        from tonsec.providers.toncenter import ToncenterProvider
        return ToncenterProvider(min_interval=0)

    def test_paginates_until_short_final_page(self):
        provider = self.provider()
        with patch.object(provider, "_get", side_effect=[
            self.page([{"hash": "a", "lt": "30"},
                       {"hash": "b", "lt": "20"}]),
            self.page([{"hash": "c", "lt": "10"}]),
        ]) as mocked:
            result = provider.transactions("test", limit=2)

        self.assertTrue(result["pagination"]["complete"])
        self.assertEqual(result["pagination"]["pages_fetched"], 2)
        self.assertEqual(result["pagination"]["returned_count"], 3)
        self.assertEqual(mocked.call_args_list[0].kwargs["sort"], "desc")
        self.assertEqual(mocked.call_args_list[1].kwargs["offset"], 2)

    def test_empty_first_page_is_complete(self):
        provider = self.provider()
        with patch.object(provider, "_get", return_value=self.page([])):
            result = provider.transactions("test", limit=5)
        self.assertTrue(result["pagination"]["complete"])
        self.assertEqual(result["pagination"]["stop_reason"], "EMPTY_PAGE")

    def test_max_pages_marks_incomplete(self):
        provider = self.provider()
        full = self.page([{"hash": "a"}, {"hash": "b"}])
        with patch.object(provider, "_get", return_value=full):
            result = provider.transactions("test", limit=2, max_pages=2)
        self.assertFalse(result["pagination"]["complete"])
        self.assertEqual(result["pagination"]["stop_reason"], "MAX_PAGES_REACHED")

    def test_429_preserves_successful_records_as_partial(self):
        provider = self.provider()
        with patch.object(provider, "_get", side_effect=[
            self.page([{"hash": "a"}, {"hash": "b"}]),
            {"ok": False, "http_status": 429, "error": "rate limited"},
        ]):
            result = provider.transactions("test", limit=2)

        self.assertTrue(result["ok"])
        self.assertTrue(result["partial"])
        self.assertFalse(result["pagination"]["complete"])
        self.assertEqual(result["pagination"]["partial_error"]["http_status"], 429)
        self.assertEqual(len(result["data"]["transactions"]), 2)

    def test_duplicate_hashes_are_removed(self):
        provider = self.provider()
        with patch.object(provider, "_get", side_effect=[
            self.page([{"hash": "a"}, {"hash": "b"}]),
            self.page([{"hash": "a"}, {"hash": "c"}]),
            self.page([]),
        ]):
            result = provider.transactions("test", limit=2)

        self.assertEqual(result["pagination"]["fetched_count"], 4)
        self.assertEqual(result["pagination"]["returned_count"], 3)
        self.assertEqual(result["pagination"]["duplicate_count"], 1)

    def test_invalid_parameters_are_rejected(self):
        provider = self.provider()
        with self.assertRaises(ValueError):
            provider.transactions("test", limit=1001)
        with self.assertRaises(ValueError):
            provider.transactions("test", limit=2, max_pages=0)

    def test_partial_endpoint_is_not_success(self):
        from tonsec.chain_audit import _endpoint_state, _collection_label
        result = {"ok": True, "pagination": {"complete": False}}
        self.assertEqual(_endpoint_state(result), "PARTIAL")
        self.assertEqual(_collection_label(result, True), "PARTIAL_RECORDS_RETURNED")

    def test_rate_interval_can_be_configured_by_environment(self):
        from tonsec.providers.toncenter import ToncenterProvider
        with patch.dict("os.environ", {"TONCENTER_MIN_INTERVAL": "0.25"}):
            provider = ToncenterProvider()
        self.assertEqual(provider.min_interval, 0.25)

    def test_rate_limiter_waits_between_requests(self):
        from tonsec.providers import toncenter
        provider = toncenter.ToncenterProvider(min_interval=1.1)
        with patch.object(toncenter, "request_json", return_value={"ok": True}):
            with patch.object(toncenter.time, "monotonic",
                              side_effect=[100.0, 100.2, 101.3]):
                with patch.object(toncenter.time, "sleep") as sleep:
                    provider._get("accountStates", "test")
                    provider._get("walletStates", "test")
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.9, places=5)

    def test_offset_pagination_reports_non_snapshot_consistency(self):
        provider = self.provider()
        with patch.object(provider, "_get", return_value=self.page([])):
            result = provider.transactions("test", limit=2)
        self.assertFalse(result["pagination"]["snapshot_stable"])
        self.assertEqual(
            result["pagination"]["consistency"],
            "OFFSET_BASED_NON_SNAPSHOT",
        )


if __name__ == "__main__":
    unittest.main()
