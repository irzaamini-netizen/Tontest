import math
import os
import time

from .common import encode_address, request_json


BASE = "https://toncenter.com/api/v3"
MAX_TRANSACTION_LIMIT = 1000
MAX_TRANSACTION_PAGES = 100


class ToncenterProvider:
    name = "toncenter"

    def __init__(self, timeout=18, min_interval=None):
        self.timeout = timeout
        if min_interval is None:
            raw_interval = os.environ.get("TONCENTER_MIN_INTERVAL", "1.1")
            try:
                min_interval = float(raw_interval)
            except (TypeError, ValueError):
                raise ValueError("TONCENTER_MIN_INTERVAL must be numeric")

        if (
            isinstance(min_interval, bool)
            or not isinstance(min_interval, (int, float))
            or not math.isfinite(min_interval)
            or min_interval < 0
        ):
            raise ValueError("min_interval must be a finite non-negative number")

        self.min_interval = float(min_interval)
        self._last_request_at = None

    def _wait_for_rate_limit(self):
        if self._last_request_at is None or self.min_interval == 0:
            return

        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _get(self, endpoint, address, **params):
        from urllib.parse import urlencode

        self._wait_for_rate_limit()
        query = {"address": address}
        query.update(params)
        url = BASE + "/" + endpoint + "?" + urlencode(query)
        result = request_json(url, self.timeout)
        self._last_request_at = time.monotonic()
        return result

    def account_states(self, address):
        return self._get("accountStates", address)

    def wallet_states(self, address):
        return self._get("walletStates", address)

    @staticmethod
    def _transaction_items(data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("transactions")
            if isinstance(items, list):
                return items
        return None

    @staticmethod
    def _transaction_hash(transaction):
        value = transaction.get("hash")
        if isinstance(value, str) and value:
            return value

        transaction_id = transaction.get("transaction_id")
        if isinstance(transaction_id, dict):
            value = transaction_id.get("hash")
            if isinstance(value, str) and value:
                return value

        return None

    def transactions(
        self,
        address,
        limit=MAX_TRANSACTION_LIMIT,
        max_pages=10,
    ):
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_TRANSACTION_LIMIT
        ):
            raise ValueError(
                "limit must be an integer between 1 and 1000"
            )

        if (
            isinstance(max_pages, bool)
            or not isinstance(max_pages, int)
            or not 1 <= max_pages <= MAX_TRANSACTION_PAGES
        ):
            raise ValueError(
                "max_pages must be an integer between 1 and 100"
            )

        transactions = []
        seen_hashes = set()
        duplicate_count = 0
        fetched_count = 0
        pages_fetched = 0
        offset = 0
        first_result = None
        stop_reason = "MAX_PAGES_REACHED"
        complete = False
        partial_error = None
        last_http_status = None

        for page_number in range(max_pages):
            result = self._get(
                "transactions",
                address,
                account=address,
                limit=limit,
                offset=offset,
                sort="desc",
            )

            if first_result is None:
                first_result = result

            last_http_status = result.get("http_status")

            if not result.get("ok"):
                stop_reason = (
                    "HTTP_429"
                    if result.get("http_status") == 429
                    else "PAGE_REQUEST_FAILED"
                )
                partial_error = {
                    "http_status": result.get("http_status"),
                    "error": result.get("error"),
                    "failed_offset": offset,
                }
                break

            items = self._transaction_items(result.get("data"))
            if items is None:
                stop_reason = "INVALID_RESPONSE_STRUCTURE"
                partial_error = {
                    "http_status": result.get("http_status"),
                    "error": (
                        "Expected a transaction list in the API response"
                    ),
                    "failed_offset": offset,
                }
                break

            pages_fetched += 1
            fetched_count += len(items)

            for transaction in items:
                if not isinstance(transaction, dict):
                    continue

                tx_hash = self._transaction_hash(transaction)
                if tx_hash is not None:
                    if tx_hash in seen_hashes:
                        duplicate_count += 1
                        continue
                    seen_hashes.add(tx_hash)

                transactions.append(transaction)

            if len(items) < limit:
                complete = True
                stop_reason = (
                    "EMPTY_PAGE" if not items else "END_OF_HISTORY"
                )
                break

            offset += limit

            if page_number == max_pages - 1:
                stop_reason = "MAX_PAGES_REACHED"

        if first_result is None:
            first_result = {
                "ok": False,
                "http_status": None,
                "error": "No transaction page was requested",
            }

        pagination = {
            "enabled": True,
            "complete": complete,
            "pages_fetched": pages_fetched,
            "page_size": limit,
            "max_pages": max_pages,
            "next_offset": offset,
            "fetched_count": fetched_count,
            "returned_count": len(transactions),
            "duplicate_count": duplicate_count,
            "stop_reason": stop_reason,
            "snapshot_stable": False,
            "consistency": "OFFSET_BASED_NON_SNAPSHOT",
            "sort": "desc",
            "min_interval": self.min_interval,
        }

        if partial_error is not None:
            pagination["partial_error"] = partial_error
            pagination["last_http_status"] = last_http_status

        if pages_fetched == 0:
            first_result["pagination"] = pagination
            return first_result

        original_data = first_result.get("data")
        if isinstance(original_data, dict):
            aggregated_data = dict(original_data)
            aggregated_data["transactions"] = transactions
        else:
            aggregated_data = {"transactions": transactions}

        output = dict(first_result)
        output["ok"] = True
        output["data"] = aggregated_data
        output["pagination"] = pagination

        if partial_error is not None:
            output["partial"] = True

        return output

    def traces(self, address, limit=5):
        return self._get(
            "traces",
            address,
            account=address,
            limit=limit,
        )

    def collect(self, address):
        return {
            "account_states": self.account_states(address),
            "wallet_states": self.wallet_states(address),
            "transactions": self.transactions(address),
            "traces": self.traces(address),
        }
