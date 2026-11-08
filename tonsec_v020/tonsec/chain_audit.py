import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .providers.common import (
    extract_count,
    normalize_account,
)
from .providers.toncenter import ToncenterProvider
from .providers.tonapi import TonapiProvider


ADDRESS_RAW = re.compile(r"^-?\d+:[0-9a-fA-F]{64}$")
ADDRESS_FRIENDLY = re.compile(r"^[A-Za-z0-9_-]{48}$")


def validate_address(value):
    if not isinstance(value, str):
        raise ValueError("Wallet address must be a string")

    value = value.strip()

    if not (
        ADDRESS_RAW.fullmatch(value)
        or ADDRESS_FRIENDLY.fullmatch(value)
    ):
        raise ValueError(
            "Unsupported TON address format. Expected raw "
            "workchain:64-hex or a 48-character friendly address."
        )

    return value


def _successful_data(result):
    if isinstance(result, dict) and result.get("ok"):
        return result.get("data")
    return None


def _observations(provider_results):
    observations = []

    center = provider_results.get("toncenter", {})
    api = provider_results.get("tonapi", {})

    account_states = _successful_data(center.get("account_states"))
    wallet_states = _successful_data(center.get("wallet_states"))
    api_account = _successful_data(api.get("account"))

    if account_states is not None:
        observations.append(
            normalize_account(
                "toncenter.accountStates",
                account_states,
                ("accounts", "account_states", "account"),
            )
        )

    if wallet_states is not None:
        observations.append(
            normalize_account(
                "toncenter.walletStates",
                wallet_states,
                ("wallets", "wallet_states", "accounts"),
            )
        )

    if api_account is not None:
        observations.append(
            normalize_account("tonapi.account", api_account)
        )

    return observations


def _comparison_key(value):
    """Compare integer-like balances without changing report values."""
    from decimal import Decimal, InvalidOperation

    if isinstance(value, bool) or value is None:
        return ("literal", json.dumps(value, sort_keys=True, default=str))

    if isinstance(value, (int, float, str)):
        try:
            return ("number", Decimal(str(value)).normalize())
        except (InvalidOperation, ValueError):
            pass

    return ("literal", json.dumps(value, sort_keys=True, default=str))


def _conflicts(observations):
    conflicts = []

    for field in (
        "status",
        "balance",
        "is_wallet",
        "code_hash",
        "data_hash",
    ):
        values = []
        for item in observations:
            value = item.get(field)
            if value is not None:
                values.append({
                    "provider": item["provider"],
                    "value": value,
                })

        distinct = {_comparison_key(item["value"]) for item in values}

        if len(distinct) > 1:
            conflicts.append({
                "field": field,
                "classification": "CONFLICTING_EVIDENCE",
                "observations": values,
                "interpretation": (
                    "Sources returned different values. "
                    "No provider is automatically treated as authoritative."
                ),
            })

    return conflicts


def _endpoint_state(result):
    if result.get("ok"):
        return "SUCCESS"
    if result.get("http_status") == 429:
        return "RATE_LIMITED"
    if result.get("http_status") is None:
        return "NETWORK_ERROR"
    return "FAILED"


def _endpoint_summary(provider_results):
    summary = {}

    for provider, endpoints in provider_results.items():
        summary[provider] = {}

        for endpoint, result in endpoints.items():
            summary[provider][endpoint] = {
                "ok": bool(result.get("ok")),
                "state": _endpoint_state(result),
                "http_status": result.get("http_status"),
                "error": result.get("error"),
                "retrieved_at": result.get("retrieved_at"),
            }

    return summary




def _address_value(value):
    if isinstance(value, dict):
        return value.get("address")
    return value if isinstance(value, str) else None


def _transaction_records(provider_results):
    records = []
    for provider, endpoints in provider_results.items():
        result = endpoints.get("transactions", {})
        data = _successful_data(result)
        if isinstance(data, dict):
            items = data.get("transactions", [])
        elif isinstance(data, list):
            items = data
        else:
            items = []

        if not isinstance(items, list):
            continue

        for tx in items:
            if isinstance(tx, dict):
                records.append({
                    "provider": provider,
                    "transaction": tx,
                })
    return records


def _message_records(records, direction):
    result = []
    for index, record in enumerate(records):
        tx = record["transaction"]
        message = tx.get("in_msg") if direction == "in" else tx.get("out_msgs", [])
        messages = [message] if isinstance(message, dict) else message
        if not isinstance(messages, list):
            continue

        for msg in messages:
            if isinstance(msg, dict):
                result.append({
                    "transaction_index": index,
                    "provider": record["provider"],
                    "transaction_hash": tx.get("hash"),
                    "message": msg,
                })
    return result


def _correlate_messages(records):
    incoming = _message_records(records, "in")
    outgoing = _message_records(records, "out")

    def index_by_hash(items):
        index = {}
        duplicates = set()
        for item in items:
            value = item["message"].get("hash")
            if not isinstance(value, str) or not value:
                continue
            if value in index:
                duplicates.add(value)
            else:
                index[value] = item
        return index, duplicates

    in_index, in_duplicates = index_by_hash(incoming)
    out_index, out_duplicates = index_by_hash(outgoing)

    correlations = []
    for msg_hash, source in out_index.items():
        if msg_hash in out_duplicates or msg_hash in in_duplicates:
            continue
        target = in_index.get(msg_hash)
        if target is None:
            continue
        if source["transaction_index"] == target["transaction_index"]:
            continue
        correlations.append({
            "message_hash": msg_hash,
            "from_transaction": source["transaction_hash"],
            "to_transaction": target["transaction_hash"],
            "from_index": source["transaction_index"],
            "to_index": target["transaction_index"],
            "source": _address_value(source["message"].get("source")),
            "destination": _address_value(source["message"].get("destination")),
            "evidence": "EXACT_MESSAGE_HASH",
        })

    return {
        "correlations": correlations,
        "unmatched_outgoing": [
            item["message"].get("hash")
            for item in outgoing
            if item["message"].get("hash") not in in_index
        ],
        "ambiguous_hashes": sorted(in_duplicates | out_duplicates),
        "incoming_count": len(incoming),
        "outgoing_count": len(outgoing),
    }


def _execution_chains(records, correlations):
    by_index = {}
    for item in correlations:
        by_index.setdefault(item["from_index"], []).append(item)

    chains = []
    for request_index, record in enumerate(records):
        tx = record["transaction"]
        inbound = tx.get("in_msg")
        if not isinstance(inbound, dict):
            continue

        # External-in messages have no internal source.
        if inbound.get("source") is not None:
            continue

        created_lt = inbound.get("created_lt")
        if created_lt not in (None, 0, "0"):
            continue

        for link in by_index.get(request_index, []):
            execution_index = link["to_index"]
            execution = records[execution_index]["transaction"]
            execution_in = execution.get("in_msg", {})
            outputs = []

            for msg in execution.get("out_msgs", []):
                if not isinstance(msg, dict):
                    continue
                source = _address_value(msg.get("source"))
                destination = _address_value(msg.get("destination"))
                inbound_destination = _address_value(
                    execution_in.get("destination")
                )
                if (
                    source is not None
                    and inbound_destination is not None
                    and source == inbound_destination
                    and destination is not None
                    and destination != source
                ):
                    outputs.append({
                        "message_hash": msg.get("hash"),
                        "destination": destination,
                        "value": msg.get("value"),
                        "opcode": msg.get("op_code"),
                    })

            chains.append({
                "request_transaction": tx.get("hash"),
                "execution_transaction": execution.get("hash"),
                "internal_message_hash": link["message_hash"],
                "external_outputs": outputs,
                "correlation_evidence": "EXACT_MESSAGE_HASH",
            })

    return chains


def analyze_transactions(provider_results):
    records = _transaction_records(provider_results)
    correlations = _correlate_messages(records)
    chains = _execution_chains(records, correlations["correlations"])

    findings = []
    failed = []
    for record in records:
        tx = record["transaction"]
        compute = tx.get("compute_phase") or {}
        action = tx.get("action_phase") or {}

        is_failed = (
            tx.get("aborted") is True
            or tx.get("success") is False
            or compute.get("success") is False
            or action.get("success") is False
        )
        if is_failed:
            item = {
                "transaction_hash": tx.get("hash"),
                "provider": record["provider"],
                "aborted": tx.get("aborted"),
                "compute_success": compute.get("success"),
                "action_success": action.get("success"),
            }
            failed.append(item)

    if failed:
        findings.append({
            "id": "TON-TX-001",
            "severity": "INFO",
            "classification": "FAILED_TRANSACTION_OBSERVED",
            "count": len(failed),
            "evidence": failed,
            "interpretation": (
                "Failed transaction evidence was observed; "
                "failure alone does not establish a vulnerability."
            ),
        })

    if correlations["ambiguous_hashes"]:
        findings.append({
            "id": "TON-TX-002",
            "severity": "INFO",
            "classification": "AMBIGUOUS_MESSAGE_HASH",
            "count": len(correlations["ambiguous_hashes"]),
            "evidence": correlations["ambiguous_hashes"],
        })

    collection = {}
    for provider, endpoints in provider_results.items():
        result = endpoints.get("transactions", {})
        data = _successful_data(result)
        if isinstance(data, dict):
            items = data.get("transactions", [])
        elif isinstance(data, list):
            items = data
        else:
            items = None

        collection[provider] = {
            "status": (
                "RECORDS_RETURNED" if isinstance(items, list)
                else _endpoint_state(result)
            ),
            "record_count": len(items) if isinstance(items, list) else None,
        }

    return {
        "status": "ANALYZED" if records else "NO_TRANSACTION_DATA",
        "transaction_count": len(records),
        "provider_collection": collection,
        "message_correlation": correlations,
        "execution_chains": chains,
        "failed_transactions": failed,
        "findings": findings,
        "limitations": [
            "Analysis covers only transactions returned by providers.",
            "Exact message-hash correlation does not prove contract safety.",
            "External message bodies and opcodes are not semantically decoded.",
            "Unmatched or ambiguous messages are not force-correlated.",
            "Provider pagination and rate limits may leave history incomplete.",
        ],
    }


def audit_wallet(address):
    address = validate_address(address)

    providers = {
        "toncenter": ToncenterProvider(),
        "tonapi": TonapiProvider(),
    }

    provider_results = {}

    jobs = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        for name, provider in providers.items():
            jobs[executor.submit(provider.collect, address)] = name

        for future in as_completed(jobs):
            name = jobs[future]
            try:
                provider_results[name] = future.result()
            except Exception as exc:
                provider_results[name] = {
                    "provider_error": {
                        "ok": False,
                        "http_status": None,
                        "error": type(exc).__name__ + ": " + str(exc),
                    }
                }

    observations = _observations(provider_results)
    conflicts = _conflicts(observations)
    transaction_analysis = analyze_transactions(provider_results)

    center = provider_results.get("toncenter", {})
    api = provider_results.get("tonapi", {})

    tx_counts = {
        "toncenter": extract_count(
            _successful_data(center.get("transactions")),
            ("transactions",),
        ),
        "tonapi": extract_count(
            _successful_data(api.get("transactions")),
            ("transactions",),
        ),
    }

    trace_count = extract_count(
        _successful_data(center.get("traces")),
        ("traces",),
    )

    endpoint_results = _endpoint_summary(provider_results)
    successful_endpoints = sum(
        item["ok"]
        for endpoints in endpoint_results.values()
        for item in endpoints.values()
    )
    total_endpoints = sum(
        len(endpoints) for endpoints in endpoint_results.values()
    )

    return {
        "schema": "tonsec.chain-audit.v1",
        "engine": "TON Security Engine",
        "engine_version": "0.2.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target": {
            "input_address": address,
            "target_type": "TON_ACCOUNT",
        },
        "mode": "READ_ONLY_CHAIN_AUDIT",
        "collection": {
            "providers": ["toncenter", "tonapi"],
            "successful_endpoints": successful_endpoints,
            "total_endpoints": total_endpoints,
            "status": (
                "COMPLETE"
                if successful_endpoints == total_endpoints
                else "PARTIAL"
                if successful_endpoints
                else "FAILED"
            ),
        },
        "account_observations": observations,
        "conflicts": conflicts,
        "activity": {
            "transaction_counts": tx_counts,
            "transaction_collection_status": {
                "toncenter": (
                    "RECORDS_RETURNED"
                    if tx_counts["toncenter"] is not None
                    else _endpoint_state(center.get("transactions", {}))
                ),
                "tonapi": (
                    "RECORDS_RETURNED"
                    if tx_counts["tonapi"] is not None
                    else _endpoint_state(api.get("transactions", {}))
                ),
            },
            "toncenter_trace_count": trace_count,
            "trace_collection_status": (
                "RECORDS_RETURNED"
                if trace_count is not None
                else _endpoint_state(center.get("traces", {}))
            ),
            "note": (
                "Counts describe returned records only; they are not "
                "complete account history. RATE_LIMITED and unavailable "
                "counts must not be interpreted as zero."
            ),
        },
        "provider_results": provider_results,
        "transaction_analysis": transaction_analysis,
        "security_assessment": {
            "status": (
                "TRANSACTIONS_ANALYZED"
                if transaction_analysis["status"] == "ANALYZED"
                else "NOT_YET_ASSESSED"
            ),
            "findings": transaction_analysis["findings"],
            "limitations": [
                "This stage collects public account and activity data only.",
                "Transaction and trace records have not yet undergone semantic security analysis.",
                "Returned transaction limits do not represent complete history.",
                "Provider disagreement is preserved and is not silently resolved.",
                "Wallet classification is not proof of contract safety.",
                "No deployed-code/source equivalence has been established.",
                "No private keys, signatures, or transactions are requested or submitted.",
            ],
        },
    }


def write_chain_report(report, outdir):
    out = Path(outdir).expanduser()

    if out.exists() and any(out.iterdir()):
        raise FileExistsError(
            "Refusing to overwrite non-empty directory: " + str(out)
        )

    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "chain_audit.json"
    md_path = out / "chain_audit.md"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = [
        "# TON Security Engine — Chain Audit",
        "",
        "- Schema: " + report["schema"],
        "- Address: `" + report["target"]["input_address"] + "`",
        "- Collection status: " + report["collection"]["status"],
        "- Successful endpoints: "
        + str(report["collection"]["successful_endpoints"])
        + "/"
        + str(report["collection"]["total_endpoints"]),
        "- Account observations: "
        + str(len(report["account_observations"])),
        "- Conflicting fields: " + str(len(report["conflicts"])),
        "",
        "## Account observations",
    ]

    if not report["account_observations"]:
        summary.append("No account observation was successfully collected.")

    for item in report["account_observations"]:
        summary += [
            "",
            "### " + item["provider"],
            "- Status: " + str(item["status"]),
            "- Balance: " + str(item["balance"]),
            "- Is wallet: " + str(item["is_wallet"]),
            "- Code hash: " + str(item["code_hash"]),
            "- Data hash: " + str(item["data_hash"]),
            "- Interfaces: " + ", ".join(item["interfaces"]),
        ]

    summary += ["", "## Conflicting evidence"]

    if not report["conflicts"]:
        summary.append("No conflict detected among available normalized fields.")

    for conflict in report["conflicts"]:
        summary += [
            "",
            "### " + conflict["field"],
            "- Classification: " + conflict["classification"],
        ]
        for observation in conflict["observations"]:
            summary.append(
                "- "
                + observation["provider"]
                + ": "
                + str(observation["value"])
            )

    summary += [
        "",
        "## Activity",
        "- Transaction counts: "
        + json.dumps(
            report["activity"]["transaction_counts"],
            ensure_ascii=False,
        ),
        "- TON Center trace count: "
        + str(report["activity"]["toncenter_trace_count"]),
        "",
        "## Transaction analysis",
        "- Analysis status: "
        + report.get("transaction_analysis", {}).get("status", "NOT_RUN"),
        "- Transactions: "
        + str(report.get("transaction_analysis", {}).get("transaction_count", 0)),
        "- Exact message correlations: "
        + str(len(report.get("transaction_analysis", {}).get(
            "message_correlation", {}).get("correlations", []))),
        "- Execution chains: "
        + str(len(report.get("transaction_analysis", {}).get(
            "execution_chains", []))),
        "",
        "## Assessment status",
        report["security_assessment"]["status"],
        "",
        "## Limitations",
    ]

    summary += [
        "- " + item
        for item in report["security_assessment"]["limitations"]
    ]

    md_path.write_text("\n".join(summary) + "\n", encoding="utf-8")

    return str(out)
