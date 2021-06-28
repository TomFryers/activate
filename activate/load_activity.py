"""Functions for loading activities from files."""
from pathlib import Path

from activate import activity, files, filetypes, track

ACTIVITY_TYPE_NAMES = {
    "run": "Run",
    "running": "Run",
    "ride": "Ride",
    "cycling": "Ride",
    "biking": "Ride",
    "walk": "Walk",
    "walking": "Walk",
    "hiking": "Walk",
    "ski": "Ski",
    "alpine_skiing": "Ski",
    "swim": "Swim",
    "swimming": "Swim",
    "row": "Row",
    "rowing": "Row",
    "1": "Ride",
    "2": "Ski",
    "9": "Run",
    "10": "Walk",
    "16": "Swim",
    "23": "Row",
}


def convert_activity_type(activity_type: str, name) -> str:
    """Get the correct activity type from a raw one or by inference."""
    activity_type = activity_type.casefold()
    if activity_type in ACTIVITY_TYPE_NAMES:
        return ACTIVITY_TYPE_NAMES[activity_type]
    if activity_type in {"unknown", "generic"}:
        # Infer activity type from name
        for activity_type_name in ACTIVITY_TYPE_NAMES:
            if activity_type_name.isnumeric():
                continue
            if name is not None and activity_type_name in name.casefold():
                return ACTIVITY_TYPE_NAMES[activity_type_name]
    return "Other"


def default_name(filename: Path):
    """Generate a default activity name from a file name."""
    return files.decode_name(filename.stem.split(".")[0])


def load(filename: Path) -> dict:
    """
    Get {"name": name, "sport": sport, "track": Track} by loading a file.

    Uses the appropriate track loader from the filetypes module.
    """
    filetype = (
        filename.with_suffix("").suffix
        if filename.suffix.casefold() == ".gz"
        else filename.suffix
    ).casefold()
    data = {".gpx": filetypes.gpx, ".fit": filetypes.fit, ".tcx": filetypes.tcx}[
        filetype
    ].load(filename)
    return {
        "name": data[0] if data[0] is not None else default_name(filename),
        "sport": convert_activity_type(data[1], data[0]),
        "track": track.Track(data[2]),
    }


def import_and_load(filename, copy_to) -> activity.Activity:
    """Import an activity and copy it into the originals directory."""
    filename = files.copy_to_location_renamed(filename, copy_to)
    return activity.from_track(**load(filename), filename=filename)
