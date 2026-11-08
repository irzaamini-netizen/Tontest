from .common import encode_address, request_json


BASE = "https://tonapi.io/v2"


class TonapiProvider:
    name = "tonapi"

    def __init__(self, timeout=18):
        self.timeout = timeout

    def _get(self, path):
        return request_json(BASE + path, self.timeout)

    def account(self, address):
        return self._get("/accounts/" + encode_address(address))

    def transactions(self, address, limit=10):
        return self._get(
            "/blockchain/accounts/"
            + encode_address(address)
            + "/transactions?limit="
            + str(limit)
        )

    def collect(self, address):
        return {
            "account": self.account(address),
            "transactions": self.transactions(address),
        }
