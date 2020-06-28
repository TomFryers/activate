import glob
import xml.etree.ElementTree

import activity
import times
import track

FIELDS = {
    "lat": lambda p: float(p.get("lat")),
    "lon": lambda p: float(p.get("lon")),
    "ele": lambda p: float(p.find("./ele").text),
    "time": lambda p: times.from_GPX(p.find("./time").text),
}


def load_gpx(filename):
    tree = xml.etree.ElementTree.iterparse(open(filename, "r"))
    for _, element in tree:
        _, _, element.tag = element.tag.rpartition("}")
    tree = tree.root
    try:
        name = tree.find("./trk/name").text
    except AttributeError:
        name = "[No Name]"
    points = tree.findall("./trk/trkseg/trkpt")
    fields = {}
    for point in points:
        for field in FIELDS:
            try:
                value = FIELDS[field](point)
            except Exception:
                continue
            if value:
                fields.setdefault(field, [])
                fields[field].append(value)

    return (name, track.Track(fields))


def load_all(directory, cache={}):
    result = []
    for filename in glob.glob(directory + "/*.gpx"):
        if filename in cache:
            data = cache[filename]
            result.append(activity.Activity(data[0], None, filename, data[1], data[2]))
            continue
        try:
            result.append(activity.from_track(*load_gpx(filename), filename))
        except ValueError:
            pass
    return result
