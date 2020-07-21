import pathlib

import fitparse

import load_activity

CONVERSION_FACTOR = 180 / 2 ** 31
FIELDS = {
    "lat": lambda p: p["position_lat"] * CONVERSION_FACTOR,
    "lon": lambda p: p["position_long"] * CONVERSION_FACTOR,
    "ele": lambda p: p["altitude"] / 5 - 500,
    "time": lambda p: p["timestamp"],
    "cadence": lambda p: p["cadence"],
    "heartrate": lambda p: p["heart_rate"],
}


def load_fit(filename):
    """Extract the fields from a FIT file."""
    fit = fitparse.FitFile(filename).messages

    sport = "unknown"
    fields = {field: [] for field in FIELDS}
    for message in fit:
        point = message.get_values()
        if message.mesg_type.name == "session":
            sport = point["sport"]

        elif message.mesg_type.name == "record":
            for field in FIELDS:
                try:
                    value = FIELDS[field](point)
                except Exception:
                    value = None
                fields[field].append(value)
    fields = {field: fields[field] for field in fields if set(fields[field]) != {None}}
    return (load_activity.decode_name(pathlib.Path(filename).stem), sport, fields)
