from dataclasses import dataclass

import requests


@dataclass
class Server:
    name: str
    address: str
    username: str
    password: str

    def post_data(self, page, data) -> bytes:
        """Send a POST request to address/page with data."""
        r = requests.post(f"{self.address}/{page}", data=data, auth=self.auth)
        r.raise_for_status()
        return r.content

    def get_data(self, page) -> bytes:
        """Send a GET request to address/page."""
        r = requests.get(f"{self.address}/{page}", auth=self.auth)
        r.raise_for_status()
        return r.content

    @property
    def auth(self):
        return requests.auth.HTTPBasicAuth(self.username, self.password)
