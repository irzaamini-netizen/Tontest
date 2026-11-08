from .common import encode_address, request_json


BASE = "https://toncenter.com/api/v3"


class ToncenterProvider:
    name = "toncenter"

    def __init__(self, timeout=18):
        self.timeout = timeout

    def _get(self, endpoint, address, **params):
        query = {"address": address}
        query.update(params)
        from urllib.parse import urlencode
        url = BASE + "/" + endpoint + "?" + urlencode(query)
        return request_json(url, self.timeout)

    def account_states(self, address):
        return self._get("accountStates", address)

    def wallet_states(self, address):
        return self._get("walletStates", address)

    def transactions(self, address, limit=10):
        return self._get(
            "transactions",
            address,
            account=address,
            limit=limit,
        )

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
