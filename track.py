import math
from functools import cached_property

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
        if "lat" not in self.fields or "lon" not in self.fields:
            raise ValueError("Missing lat or lon in Track field")

    @cached_property
    def lat_lon_list(self):
        return [[x, y] for x, y in zip(self.fields["lat"], self.fields["lon"])]

    @cached_property
    def length(self):
        if "ele" in self.fields:
            elevation_data = self.fields["ele"]
        else:
            elevation_data = [0 for _ in range(len(self.fields["lat"]))]

        points = list(zip(self.fields["lat"], self.fields["lon"], elevation_data))
        return sum(
            point_distance(points[p], points[p - 1]) for p in range(1, len(points))
        )

    @cached_property
    def ascent(self):
        if "ele" in self.fields:
            return sum(
                max(self.fields["ele"][p] - self.fields["ele"][p - 1], 0)
                for p in range(1, len(self.fields["ele"]) - 1)
            )

    @cached_property
    def elapsed_time(self):
        start_time = self.fields["time"][0]
        end_time = self.fields["time"][-1]
        return end_time - start_time


    @cached_property
    def average_speed(self):
        duration = self.elapsed_time.total_seconds()
        return self.length / duration

