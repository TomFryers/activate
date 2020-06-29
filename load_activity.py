import glob

import activity
import load_fit
import load_gpx
import track


def has_extension(filename, extension) -> bool:
    """Determine if a file path has a given extension."""
    return filename.casefold().endswith("." + extension)


def load(filename):
    """Get a (name, Track) tuple by loading from a file."""
    if has_extension(filename, "gpx"):
        data = load_gpx.load_gpx(filename)
    elif has_extension(filename, "fit"):
        data = load_fit.load_fit(filename)

    return (data[0], track.Track(data[1]))


def load_all(directory, cache={}):
    """Get all activities in a directory."""
    result = []
    for filename in glob.glob(directory + "/*"):
        # Create cached activity
        if filename in cache:
            data = cache[filename]
            result.append(activity.Activity(data[0], None, filename, data[1], data[2]))
            continue
        # Create normal activity
        try:
            result.append(activity.from_track(*load(filename), filename))
        # Raised by files with no latitude or longitude
        except ValueError:
            pass
    return result
