import xml.etree.ElementTree

import times

FIELDS = {
    "lat": lambda p: float(p.get("lat")),
    "lon": lambda p: float(p.get("lon")),
    "ele": lambda p: float(p.find("./ele").text),
    "time": lambda p: times.from_GPX(p.find("./time").text),
}


def load_gpx(filename):
    """Extract the fields from a GPX file."""
    # Load the tree, getting rid of namespaces
    tree = xml.etree.ElementTree.iterparse(open(filename, "r"))
    for _, element in tree:
        _, _, element.tag = element.tag.rpartition("}")
    tree = tree.root
    # Find the activity name
    try:
        name = tree.find("./trk/name").text
    except AttributeError:
        name = "[No Name]"

    points = tree.findall("./trk/trkseg/trkpt")
    fields = {field: [] for field in FIELDS}
    for point in points:
        for field in FIELDS:
            value = None
            try:
                value = FIELDS[field](point)
            except Exception:
                value = None
            fields[field].append(value)
    fields = {field: fields[field] for field in fields if set(fields[field]) != {None}}

    return (name, fields)
