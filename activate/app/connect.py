import requests


def post_data(address, page, data) -> bytes:
    r = requests.post(f"{address}/{page}", data=data)
    r.raise_for_status()
    return r.content


def get_data(address, page) -> bytes:
    r = requests.get(f"{address}/{page}")
    r.raise_for_status()
    return r.content
