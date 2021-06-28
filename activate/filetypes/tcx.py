"""Load the fields from a GPX file on disk."""
from activate import times
from activate.filetypes import load_xml

FIELDS = {
    "lat": lambda p: float(p.find("./Position/LatitudeDegrees").text),
    "lon": lambda p: float(p.find("./Position/LongitudeDegrees").text),
    "ele": lambda p: float(p.find("./AltitudeMeters").text),
    "time": lambda p: times.from_GPX(p.find("./Time").text),
    "speed": lambda p: float(p.find("./Extensions/TPX/Speed").text),
    "distance": lambda p: float(p.find("./DistanceMeters").text),
    "cadence": lambda p: float(p.find("./Extensions/TPX/RunCadence").text) / 60,
    "heartrate": lambda p: float(p.find("./HeartRateBpm").text) / 60,
    "power": lambda p: float(p.find("./Extensions/TPX/Watts").text),
}


def load(filename):
    """Extract the fields from a TCX file."""
    tree = load_xml.get_tree(filename)
    # Find the sport
    try:
        sport = tree.find("./Activities/Activity").get("Sport")
    except AttributeError:
        sport = "unknown"

    points = tree.findall("./Activities/Activity/Lap/Track/Trackpoint")
    return (None, sport, load_xml.load_fields(points, FIELDS))
