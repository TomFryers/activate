import requests


def post_data(address, page, data) -> bytes:
    """Send a POST request to address/page with data."""
    r = requests.post(f"{address}/{page}", data=data)
    r.raise_for_status()
    return r.content


def get_data(address, page) -> bytes:
    """Send a GET request to address/page."""
    r = requests.get(f"{address}/{page}")
    r.raise_for_status()
    return r.content
