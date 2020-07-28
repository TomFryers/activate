"""Load the fields from a GPX file on disk."""
import pathlib
import xml.etree.ElementTree

from activate.core import files, times


def try_multi(point, locations):
    """Try to search for a value in several positions."""
    for location in locations:
        try:
            return point.find(location).text
        except AttributeError:
            continue
    return None


FIELDS = {
    "lat": lambda p: float(p.get("lat")),
    "lon": lambda p: float(p.get("lon")),
    "ele": lambda p: float(p.find("./ele").text),
    "time": lambda p: times.from_GPX(p.find("./time").text),
    "speed": lambda p: float(p.find("./extensions/speed").text),
    "distance": lambda p: float(p.find("./extensions/distance").text),
    "cadence": lambda p: float(
        try_multi(p, ("./extensions/cadence", "./extensions/TrackPointExtension/cad",),)
    )
    / 60,
    "heartrate": lambda p: float(
        try_multi(
            p,
            (
                "./extensions/heartrate",
                "./extensions/hr",
                "./extensions/TrackPointExtension/hr",
            ),
        )
    )
    / 60,
    "power": lambda p: float(p.find("./extensions/power").text),
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
        name = files.decode_name(pathlib.Path(filename).stem)

    try:
        sport = tree.find("./trk/type").text
        print(f"{sport=} {name=}")
    except AttributeError:
        sport = "unknown"

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
    return (name, sport, fields)
