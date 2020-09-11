"""Functions for loading activities from files."""

from activate.core import activity, files, filetypes, track

ACTIVITY_TYPE_NAMES = {
    "running": "Run",
    "cycling": "Ride",
    "run": "Run",
    "ride": "Ride",
    "hiking": "Walk",
    "alpine_skiing": "Ski",
    "swimming": "Swim",
    "rowing": "Row",
    "driving": "Other",
    "9": "Run",
    "1": "Ride",
    "16": "Swim",
}


def convert_activity_type(activity_type: str, name) -> str:
    """Get the correct activity type from a raw one or by inference."""
    if activity_type in {"unknown", "generic"}:
        # Infer activity type from name
        for activity_type_name in ACTIVITY_TYPE_NAMES:
            if activity_type_name.isnumeric():
                continue
            if activity_type_name in name.casefold():
                return ACTIVITY_TYPE_NAMES[activity_type_name]
        return ""
    return ACTIVITY_TYPE_NAMES[activity_type.casefold()]


def load(filename) -> dict:
    """
    Get {"name": name, "sport": sport, "track": Track} by loading a file.

    Uses the appropriate track loader from the filetypes module.
    """
    if files.has_extension(filename, "gpx"):
        data = filetypes.gpx.load_gpx(filename)
    elif files.has_extension(filename, "fit"):
        data = filetypes.fit.load_fit(filename)

    return {
        "name": data[0],
        "sport": convert_activity_type(data[1], data[0]),
        "track": track.Track(data[2]),
    }


def import_and_load(filename, copy_to) -> activity.Activity:
    """Import an activity and copy it into the originals directory."""
    filename = files.copy_to_location_renamed(filename, copy_to)
    return activity.from_track(**load(filename), filename=filename)
