import xml.etree.ElementTree

NAMESPACE = "{http://www.topografix.com/GPX/1/1}"


def load_gpx(filename):
    tree = xml.etree.ElementTree.parse(filename).getroot()
    points = tree.findall(f"./{NAMESPACE}trk/{NAMESPACE}trkseg/{NAMESPACE}trkpt")
    return [[float(point.get("lat")), float(point.get("lon"))] for point in points]
