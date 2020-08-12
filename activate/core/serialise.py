import datetime
import json


def default(obj):
    """
    Turn datetimes and timedeltas into JSON.

    >>> default(datetime.datetime(2000, 1, 2, 12, 30, 42))
    {'__DATETIME': '2000-01-02T12:30:42'}
    >>> default(datetime.timedelta(minutes=1, seconds=40))
    {'__TIMEDELTA': 100.0}
    """
    if isinstance(obj, datetime.datetime):
        return {"__DATETIME": obj.isoformat()}
    if isinstance(obj, datetime.timedelta):
        return {"__TIMEDELTA": obj.total_seconds()}
    raise TypeError(f"Cannot serialise {obj.__class__.__qualname__}")


def decode(obj):
    """Undo encoding done by default."""
    if len(obj) == 1:
        first_key = next(iter(obj.keys()))
        if first_key == "__DATETIME":
            return datetime.datetime.fromisoformat(obj["__DATETIME"])
        if first_key == "__TIMEDELTA":
            return datetime.timedelta(seconds=obj["__TIMEDELTA"])
    return obj


def dump_file(obj, filename):
    """Save obj as a JSON file. Can store datetimes and timedeltas."""
    with open(filename, "w") as f:
        json.dump(obj, f, default=default)


def load_file(filename):
    """Load a JSON file. Can retrieve datetimes and timedeltas."""
    with open(filename, "r") as f:
        return json.load(f, object_hook=decode)
