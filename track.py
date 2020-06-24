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
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

    @property
    def lat_lon_list(self):
        return [[x, y] for x, y in zip(self.fields["lat"], self.fields["lon"])]

    @property
    def length(self):
        points = list(zip(self.fields["lat"], self.fields["lon"], self.fields["ele"]))
        return sum(
            point_distance(points[p], points[p - 1]) for p in range(1, len(points))
        )

    @property
    def ascent(self):
        return sum(
            max(self.fields["ele"][p] - self.fields["ele"][p - 1], 0)
            for p in range(1, len(self.fields["ele"]) - 1)
        )

    @property
    def elapsed_time(self):
        start_time = self.fields["time"][0]
        end_time = self.fields["time"][-1]
        return end_time - start_time

    @property
    def start_time(self):
        return self.fields["time"][0]

    @property
    def average_speed(self):
        return self.length / self.elapsed_time.total_seconds()
