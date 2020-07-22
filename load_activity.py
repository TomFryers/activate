import glob
import pathlib
import shutil

import activity
import load_fit
import load_gpx
import track

TRACK_DIR = "originals"

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


def encode_name(filename, current_filenames):
    """
    Rename a file to avoid name collisions.

    Renames foo.gpx to _0_foo.gpx if foo.gpx already exists. If that
    exists tries _1_foo.gpx, _2_foo.gpx... until a free name is found.
    If the name already starts with an underscore, it is replaced with a
    double underscore, so _foo_bar.gpx becomes __foo_bar.gpx,
    _0___foo_bar.gpx etc.
    """
    if filename[0] == "_":
        filename = "_" + filename
    full_name = f"{TRACK_DIR}/{filename}"
    i = 0
    while full_name in current_filenames:
        full_name = f"{TRACK_DIR}/_{i}_{filename}"
        i += 1
    return full_name


def decode_name(filename):
    """Get a file's original name from its encoded one."""
    if filename[0] != "_":
        return filename
    filename = filename[filename[1:].index("_") + 2 :]
    if filename.startswith("__"):
        return filename[2:]
    return filename


def import_and_load(filename) -> activity.Activity:
    """Import an activity and copy it into the originals directory."""
    filename = pathlib.Path(filename)
    filenames = glob.glob(f"{TRACK_DIR}/*")
    out_name = encode_name(filename.name, filenames)
    shutil.copy2(filename, out_name)
    return activity.from_track(*load(str(out_name)), str(out_name))
