import pathlib

import fitparse

CONVERSION_FACTOR = 180 / 2 ** 31
FIELDS = {
    "lat": lambda p: p["position_lat"] * CONVERSION_FACTOR,
    "lon": lambda p: p["position_long"] * CONVERSION_FACTOR,
    "ele": lambda p: p["altitude"] / 5 - 500,
    "time": lambda p: p["timestamp"],
}


def load_fit(filename):
    fit = fitparse.FitFile(filename).messages

    fields = {}
    for message in fit:
        point = message.get_values()
        for field in FIELDS:
            try:
                value = FIELDS[field](point)
            except Exception:
                continue
            if value:
                fields.setdefault(field, [])
                fields[field].append(value)
    return (pathlib.Path(filename).stem, fields)
