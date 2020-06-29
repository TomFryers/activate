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
    """Extract the fields from a FIT file."""
    fit = fitparse.FitFile(filename).messages

    fields = {field: [] for field in FIELDS}
    for message in fit:
        point = message.get_values()
        for field in FIELDS:
            try:
                value = FIELDS[field](point)
            except Exception:
                value = None
            fields[field].append(value)
    fields = {field: fields[field] for field in fields if set(fields[field]) != {None}}
    return (pathlib.Path(filename).stem, fields)
