import xml.etree.ElementTree

import track

NAMESPACE = "{http://www.topografix.com/GPX/1/1}"

FIELDS = {
    "lat": lambda p: float(p.get("lat")),
    "lon": lambda p: float(p.get("lon")),
    "ele": lambda p: float(p.find(f"./{NAMESPACE}ele").text),
}


def load_gpx(filename):
    tree = xml.etree.ElementTree.parse(filename).getroot()
    points = tree.findall(f"./{NAMESPACE}trk/{NAMESPACE}trkseg/{NAMESPACE}trkpt")
    fields = {}
    for point in points:
        for field in FIELDS:
            value = FIELDS[field](point)
            if value:
                fields.setdefault(field, [])
                fields[field].append(value)

    return track.Track(fields)
