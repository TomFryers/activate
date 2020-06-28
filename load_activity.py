import glob

import activity
import load_fit
import load_gpx
import track


def load(filename):
    if filename.casefold().endswith(".gpx"):
        data = load_gpx.load_gpx(filename)
    elif filename.casefold().endswith(".fit"):
        data = load_fit.load_fit(filename)

    return (data[0], track.Track(data[1]))


def load_all(directory, cache={}):
    result = []
    for filename in glob.glob(directory + "/*"):
        if filename in cache:
            data = cache[filename]
            result.append(activity.Activity(data[0], None, filename, data[1], data[2]))
            continue
        try:
            result.append(activity.from_track(*load(filename), filename))
        except ValueError:
            pass
    return result
