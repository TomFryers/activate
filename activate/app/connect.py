from dataclasses import dataclass

import requests

from activate import serialise

TIMEOUT = 4


@dataclass
class Server:
    address: str
    name: str
    username: str
    password: str

    def post_data(self, page, data) -> bytes:
        """Send a POST request to address/page with data."""
        r = requests.post(
            self.api_address(page), data=data, auth=self.auth, timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.content

    def get_data(self, page) -> bytes:
        """Send a GET request to address/page."""
        r = requests.get(self.api_address(page), auth=self.auth, timeout=TIMEOUT)
        r.raise_for_status()
        return r.content

    def upload_activity(self, activity):
        self.post_data(
            "send_activity", {"activity": serialise.dump_bytes(activity.save_data)}
        )

    def api_address(self, page):
        return f"{self.address.rstrip('/')}/api/{page}"

    @property
    def auth(self):
        return requests.auth.HTTPBasicAuth(self.username, self.password)
