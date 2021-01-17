"""Functions for loading activities from files."""

from collections import defaultdict

from activate import activity, files, filetypes, track

ACTIVITY_TYPE_NAMES = {
    "running": "Run",
    "cycling": "Ride",
    "run": "Run",
    "ride": "Ride",
    "hiking": "Walk",
    "walk": "Walk",
    "walking": "Walk",
    "alpine_skiing": "Ski",
    "ski": "Ski",
    "swimming": "Swim",
    "swim": "Swim",
    "rowing": "Row",
    "row": "Row",
    "9": "Run",
    "1": "Ride",
    "16": "Swim",
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
            if activity_type_name in name.casefold():
                return ACTIVITY_TYPE_NAMES[activity_type_name]
    return "Other"


def load(filename) -> dict:
    """
    Get {"name": name, "sport": sport, "track": Track} by loading a file.

    Uses the appropriate track loader from the filetypes module.
    """
    filetype = (
        filename.with_suffix("").suffix
        if filename.suffix.casefold() == ".gz"
        else filename.suffix
    ).casefold()
    if filetype == ".gpx":
        data = filetypes.gpx.load_gpx(filename)
    elif filetype == ".fit":
        data = filetypes.fit.load_fit(filename)
    elif filetype == ".tcx":
        data = filetypes.tcx.load_tcx(filename)
    else:
        raise ValueError("Invalid filetype")

    return {
        "name": data[0],
        "sport": convert_activity_type(data[1], data[0]),
        "track": track.Track(data[2]),
    }


def import_and_load(filename, copy_to) -> activity.Activity:
    """Import an activity and copy it into the originals directory."""
    filename = files.copy_to_location_renamed(filename, copy_to)
    return activity.from_track(**load(filename), filename=filename)
