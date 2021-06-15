"""Load and parse FIT files."""
import gzip

from fitparse import FitFile

CONVERSION_FACTOR = 180 / 2 ** 31
UNIVERSAL_FIELDS = {"time": lambda p: p["timestamp"], "dist": lambda p: p["distance"]}
NORMAL_FIELDS = {
    **UNIVERSAL_FIELDS,
    **{
        "lat": lambda p: p["position_lat"] * CONVERSION_FACTOR,
        "lon": lambda p: p["position_long"] * CONVERSION_FACTOR,
        "ele": lambda p: p["altitude"],
        "cadence": lambda p: p["cadence"] / 60,
        "heartrate": lambda p: p["heart_rate"] / 60,
        "speed": lambda p: p["speed"],
        "power": lambda p: p["power"],
    },
}

LENGTH_SWIM_FIELDS = {
    **UNIVERSAL_FIELDS,
    **{"speed": lambda p: p["speed"], "stroke": lambda p: p["swim_stroke"]},
}


def load(filename):
    """Load and parse a FIT file."""
    if filename.suffix == ".gz":
        with gzip.open(filename) as f:
            fit = FitFile(f).messages
    else:
        fit = FitFile(str(filename)).messages
    fit = list(fit)
    for message in fit:
        point = message.get_values()
        if point.items() & {"sub_sport": "lap_swimming", "event": "length"}.items():
            return parse_fit(filename, fit, LENGTH_SWIM_FIELDS)
    return parse_fit(filename, fit, NORMAL_FIELDS)


def parse_fit(filename, fit, available_fields):
    """Extract the useful fields from a FIT file."""
    sport = "unknown"
    fields = {field: [] for field in available_fields}
    for message in fit:
        point = message.get_values()
        if message.mesg_type.name == "session":
            sport = point["sport"]

        elif message.mesg_type.name == "record":
            for field in available_fields:
                try:
                    value = available_fields[field](point)
                except Exception:
                    value = None
                fields[field].append(value)
    fields = {field: fields[field] for field in fields if set(fields[field]) != {None}}
    return (None, sport, fields)
