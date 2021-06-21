import math
from datetime import timedelta

from activate import times


def as_int(value) -> str:
    """Format a value as an integer, ready to display."""
    return str(round(value))


def maybe_as_int(value) -> str:
    """
    Format a value as an integer if it is one.

    Any very close value will be formatted as an integer to avoid
    floating-point errors.
    """
    if math.isclose(value, round(value)):
        return as_int(value)
    return str(value)


def info_format(entry: str):
    """Format an value for the info box."""
    if entry in {"Average Speed", "Mov. Av. Speed", "Distance"}:
        return "{:.2f}".format
    if entry in {"Max. Speed", "Average Power", "Average HR", "Avg. Cadence"}:
        return "{:.1f}".format
    if entry in {"Ascent", "Descent", "Highest Point", "Max. Power"}:
        return as_int
    if entry in {"Elapsed Time", "Moving Time", "Pace", "Pace (mov.)"}:
        return times.to_string
    if entry is None:
        return lambda x: x
    raise ValueError(f"Unknown entry: {entry}")


def split_format(entry: str):
    """Format a value for the splits table."""
    if entry == "Number":
        return as_int
    if entry in {"Time", "Split"}:
        return times.to_string
    if entry in {"Net Climb", "Ascent"}:
        return as_int
    if entry == "Speed":
        return "{:.2f}".format
    raise ValueError(f"Unknown entry: {entry}")


def list_format(entry: str):
    """Format a value for the splits table."""
    if entry in {"Name", "Type", "Server", "User"}:
        return None
    if entry == "Distance":
        return "{:.2f}".format
    if entry == "Start Time":
        return lambda value: str(times.round_time(value))
    raise ValueError(f"Unknown entry: {entry}")


def default_as_string(value) -> str:
    """
    Round a value in a sensible way.

    Always shows at least the nearest integer. Any extra precision is
    limited to the lesser of two decimal places, or three significant
    figures. Also formats timedeltas nicely.
    """
    if isinstance(value, tuple):
        suffix = " " + value[1]
        value = value[0]
    else:
        suffix = ""
    if isinstance(value, timedelta):
        return times.to_string(value)
    if value >= 100:
        return as_int(value) + suffix
    if value >= 10:
        return str(round(value, 1)) + suffix
    return str(round(value, 2)) + suffix
