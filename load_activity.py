import glob
import pathlib
import shutil

import activity
import load_fit
import load_gpx
import track

TRACK_DIR = "tracks"

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


def convert_activity_type(activity_type, name):
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


def has_extension(filename, extension) -> bool:
    """Determine if a file path has a given extension."""
    return filename.casefold().endswith("." + extension)


def load(filename):
    """Get a (name, sport, Track) tuple by loading from a file."""
    if has_extension(filename, "gpx"):
        data = load_gpx.load_gpx(filename)
    elif has_extension(filename, "fit"):
        data = load_fit.load_fit(filename)

    return (data[0], convert_activity_type(data[1], data[0]), track.Track(data[2]))


def decode_name(filename):
    if filename[0] != "_":
        return filename
    filename = filename[filename[1:].index("_") + 2 :]
    if filename.startswith("__"):
        return filename[2:]
    return filename


def import_and_load(filename):
    filename = pathlib.Path(filename)
    filenames = glob.glob(f"{TRACK_DIR}/*")
    out_name = filename.name
    if out_name[0] == "_":
        out_name = "_" + out_name
    real_out_name = f"{TRACK_DIR}/{out_name}"
    i = 0
    while real_out_name in filenames:
        real_out_name = f"{TRACK_DIR}/_{i}_{out_name}"
        i += 1
    shutil.copy2(filename, real_out_name)
    return activity.from_track(*load(str(real_out_name)), str(real_out_name))


def load_all(directory, cache=None):
    """Get all activities in a directory."""
    if cache is None:
        cache = {}
    result = []
    for filename in glob.glob(directory + "/*"):
        # Create cached activity
        if filename in cache:
            data = cache[filename]
            result.append(
                activity.Activity(data[0], data[1], None, filename, data[2], data[3])
            )
            continue
        # Create normal activity
        try:
            result.append(activity.from_track(*load(filename), filename))
        # Raised by files with no latitude or longitude
        except ValueError:
            pass
    return result
