import glob
import xml.etree.ElementTree

import track
import times

NAMESPACE = "{http://www.topografix.com/GPX/1/1}"

FIELDS = {
    "lat": lambda p: float(p.get("lat")),
    "lon": lambda p: float(p.get("lon")),
    "ele": lambda p: float(p.find(f"./{NAMESPACE}ele").text),
    "time": lambda p: times.from_GPX(p.find(f"./{NAMESPACE}time").text),
}


def load_gpx(filename):
    tree = xml.etree.ElementTree.parse(filename).getroot()
    name = tree.find(f"./{NAMESPACE}trk/{NAMESPACE}name").text
    points = tree.findall(f"./{NAMESPACE}trk/{NAMESPACE}trkseg/{NAMESPACE}trkpt")
    fields = {}
    for point in points:
        for field in FIELDS:
            value = FIELDS[field](point)
            if value:
                fields.setdefault(field, [])
                fields[field].append(value)

    return track.Track(name, fields)


def load_all(directory):
    return [load_gpx(f) for f in glob.glob(directory + "/*.gpx")]
