"""Functions for loading activities from files."""
import glob
import pathlib
import shutil

from activate.core import activity, files, track, filetypes

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


def load(filename) -> tuple:
    """Get a (name, sport, Track) tuple by loading from a file."""
    if files.has_extension(filename, "gpx"):
        data = filetypes.gpx.load_gpx(filename)
    elif files.has_extension(filename, "fit"):
        data = filetypes.fit.load_fit(filename)

    return (data[0], convert_activity_type(data[1], data[0]), track.Track(data[2]))


def import_and_load(filename, copy_to) -> activity.Activity:
    """Import an activity and copy it into the originals directory."""
    filename = pathlib.Path(filename)
    filenames = glob.glob(f"{copy_to}*")
    out_name = files.encode_name(filename.name, filenames, copy_to)
    shutil.copy2(filename, out_name)
    return activity.from_track(*load(str(out_name)), str(out_name))
