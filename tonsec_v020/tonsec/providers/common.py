import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


USER_AGENT = "TON-Security-Engine/0.2.0"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def request_json(url, timeout=18):
    retrieved_at = utc_now()
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read(8 * 1024 * 1024 + 1)

        if len(body) > 8 * 1024 * 1024:
            return {
                "ok": False,
                "http_status": status,
                "error": "Response exceeded 8 MiB limit",
                "retrieved_at": retrieved_at,
                "url": url,
            }

        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return {
                "ok": False,
                "http_status": status,
                "error": "Invalid JSON response: " + str(exc),
                "retrieved_at": retrieved_at,
                "url": url,
            }

        return {
            "ok": True,
            "http_status": status,
            "data": data,
            "retrieved_at": retrieved_at,
            "url": url,
        }

    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read(4096).decode("utf-8", errors="replace")
        except Exception:
            detail = ""

        return {
            "ok": False,
            "http_status": exc.code,
            "error": "HTTPError: " + detail[:1000],
            "retrieved_at": retrieved_at,
            "url": url,
        }

    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "http_status": None,
            "error": type(exc).__name__ + ": " + str(exc),
            "retrieved_at": retrieved_at,
            "url": url,
        }


def encode_address(address):
    return urllib.parse.quote(address, safe="")


def first_record(data, keys):
    if isinstance(data, list):
        return data[0] if data and isinstance(data[0], dict) else {}

    if not isinstance(data, dict):
        return {}

    for key in keys:
        value = data.get(key)
        if isinstance(value, list) and value:
            if isinstance(value[0], dict):
                return value[0]
        if isinstance(value, dict):
            return value

    return data


def normalize_account(provider, data, record_keys=()):
    record = first_record(data, record_keys)

    def pick(*names):
        for name in names:
            if name in record and record[name] is not None:
                return record[name]
        return None

    interfaces = pick("interfaces", "interface")
    if isinstance(interfaces, str):
        interfaces = [interfaces]
    elif not isinstance(interfaces, list):
        interfaces = []

    return {
        "provider": provider,
        "status": pick("status", "account_status", "state"),
        "balance": pick("balance"),
        "is_wallet": pick("is_wallet", "isWallet"),
        "code_hash": pick("code_hash", "codeHash"),
        "data_hash": pick("data_hash", "dataHash"),
        "interfaces": interfaces,
        "last_transaction_lt": pick(
            "last_transaction_lt", "lastTransactionLt"
        ),
        "last_transaction_hash": pick(
            "last_transaction_hash", "lastTransactionHash"
        ),
        "record_available": bool(record),
    }


def extract_count(data, keys):
    if isinstance(data, list):
        return len(data)

    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return len(value)

    return None
