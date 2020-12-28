"""
Functions for serialising and deserialising objects to JSON.

The JSON can optionally be gzipped.
"""
import gzip
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path


def default(obj):
    """
    Turn datetimes and timedeltas into JSON.

    >>> default(datetime(2000, 1, 2, 12, 30, 42))
    {'__DATETIME': '2000-01-02T12:30:42'}
    >>> default(timedelta(minutes=1, seconds=40))
    {'__TIMEDELTA': 100.0}
    """
    if isinstance(obj, datetime):
        return {"__DATETIME": obj.isoformat()}
    if isinstance(obj, timedelta):
        return {"__TIMEDELTA": obj.total_seconds()}
    if isinstance(obj, uuid.UUID):
        return {"__ID": str(obj)}
    if isinstance(obj, Path):
        return {"__PATH": str(obj)}
    raise TypeError(f"Cannot serialise {obj.__class__.__qualname__}")


def decode(obj):
    """Undo encoding done by default."""
    if len(obj) == 1:
        ((key, value),) = obj.items()
        if key == "__DATETIME":
            return datetime.fromisoformat(value)
        if key == "__TIMEDELTA":
            return timedelta(seconds=value)
        if key == "__ID":
            return uuid.UUID(value)
        if key == "__PATH":
            return Path(value)
    return obj


def dumps(obj, readable=False):
    """Convert an object to a JSON string."""
    return json.dumps(
        obj,
        default=default,
        separators=None if readable else (",", ":"),
        indent="\t" if readable else None,
    )


def dump_bytes(obj, gz=False, readable=False):
    """Convert an object to data."""
    data = dumps(obj, readable=readable).encode("utf-8")
    return gzip.compress(data) if gz else data


def loads(data):
    """Load an object from a string."""
    return json.loads(data, object_hook=decode)


def load_bytes(data, gz=False):
    """Load an object from data."""
    data = gzip.decompress(data) if gz else data
    return loads(data.decode("utf-8"))


def dump(obj, filename, *args, **kwargs):
    """
    Save obj as a JSON file. Can store datetimes and timedeltas.

    Can be gzipped if gz is True.
    """
    with open(filename, "wb") as f:
        f.write(dump_bytes(obj, *args, **kwargs))


def load(filename: Path, gz="auto"):
    """Load a JSON file. Can retrieve datetimes and timedeltas."""
    if gz == "auto":
        gz = filename.suffix.casefold() == ".gz"
    with open(filename, "rb") as f:
        return load_bytes(f.read(), gz=gz)
