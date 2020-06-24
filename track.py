import math

EARTH_RADIUS = 6371008.7714

# TODO Use proper formula
def to_cartesian(lat, lon, ele):
    lat = math.radians(lat)
    lon = math.radians(lon)
    return (
        (EARTH_RADIUS + ele) * math.cos(lat) * math.cos(lon),
        (EARTH_RADIUS + ele) * math.cos(lat) * math.sin(lon),
        (EARTH_RADIUS + ele) * math.sin(lat),
    )


def point_distance(point1, point2):
    point1 = to_cartesian(*point1)
    point2 = to_cartesian(*point2)
    return sum((point1[i] - point2[i]) ** 2 for i in range(3)) ** 0.5


class Track:
    def __init__(self, fields):
        self.fields = fields

    @property
    def lat_lon_list(self):
        return [[x, y] for x, y in zip(self.fields["lat"], self.fields["lon"])]

    @property
    def length(self):
        points = list(
            zip(self.fields["lat"][1:], self.fields["lon"][1:], self.fields["ele"][1:])
        )
        return sum(
            point_distance(points[p], points[p - 1]) for p in range(1, len(points))
        )
