import math
from functools import cached_property

EARTH_RADIUS = 6371008.7714
SPEED_RANGE = 2

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

        if self.has_altitude_data:
            elevation_data = self.fields["ele"]
        else:
            elevation_data = [0 for _ in range(len(self.fields["lat"]))]

        points = list(
            zip(
                self.fields["lat"],
                self.fields["lon"],
                elevation_data,
                self.fields["time"],
            )
        )
        total_dist = 0
        self.fields["dist"] = [0]
        for p in range(1, len(points)):
            total_dist += point_distance(points[p][:3], points[p - 1][:3])
            self.fields["dist"].append(total_dist)
        self.length = total_dist

        self.fields["speed"] = []
        for point_index in range(0, len(points)):
            relevant_points = [
                point_index + i for i in range(-SPEED_RANGE, SPEED_RANGE + 1)
            ]
            while relevant_points[0] < 0:
                relevant_points.pop(0)
            while relevant_points[-1] >= len(points):
                relevant_points.pop(-1)
            relevant_points = [points[p] for p in relevant_points]
            time_diff = (relevant_points[-1][3] - relevant_points[0][3]).total_seconds()
            distance = sum(
                point_distance(relevant_points[p][:3], relevant_points[p - 1][:3])
                for p in range(1, len(relevant_points))
            )
            if time_diff:
                self.fields["speed"].append(distance / time_diff)
            else:
                self.fields["speed"].append(self.fields["speed"][-1])

    @property
    def has_altitude_data(self):
        return "ele" in self.fields

    @cached_property
    def lat_lon_list(self):
        return [[x, y] for x, y in zip(self.fields["lat"], self.fields["lon"])]

    @cached_property
    def ascent(self):
        if self.has_altitude_data:
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
