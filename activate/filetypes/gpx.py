"""Load the fields from a GPX file on disk."""
from activate import times
from activate.filetypes import load_xml

CADENCE_FIELDS = ("./extensions/cadence", "./extensions/TrackPointExtension/cad")
HEART_RATE_FIELDS = (
    "./extensions/heartrate",
    "./extensions/hr",
    "./extensions/TrackPointExtension/hr",
)
FIELDS = {
    "lat": lambda p: float(p.get("lat")),
    "lon": lambda p: float(p.get("lon")),
    "ele": lambda p: float(p.find("./ele").text),
    "time": lambda p: times.from_GPX(p.find("./time").text),
    "speed": lambda p: float(p.find("./extensions/speed").text),
    "distance": lambda p: float(p.find("./extensions/distance").text),
    "cadence": lambda p: float(load_xml.try_multi(p, CADENCE_FIELDS)) / 60,
    "heartrate": lambda p: float(load_xml.try_multi(p, HEART_RATE_FIELDS)) / 60,
    "power": lambda p: float(p.find("./extensions/power").text),
}


def load_gpx(filename) -> tuple:
    """Extract the fields from a GPX file."""
    tree = load_xml.get_tree(filename)
    # Find the activity name
    try:
        name = tree.find("./trk/name").text
    except AttributeError:
        name = None

    # Find the sport
    try:
        sport = tree.find("./trk/type").text
        print(f"{sport=} {name=}")
    except AttributeError:
        sport = "unknown"

    points = tree.findall("./trk/trkseg/trkpt")
    return (name, sport, load_xml.load_fields(points, FIELDS))
