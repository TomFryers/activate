import math
from functools import cached_property

EARTH_RADIUS = 6378137
E_2 = 0.00669437999014
SPEED_RANGE = 2


def to_cartesian(lat, lon, ele):
    """Convert from geodetic to cartesian coordinates based on WGS 84."""
    if None in {lat, lon, ele}:
        return (None, None, None)
    lat = math.radians(lat)
    lon = math.radians(lon)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)
    partial_radius = EARTH_RADIUS / math.sqrt(1 - E_2 * sin_lat ** 2)
    lat_radius = (ele + partial_radius) * cos_lat
    return (
        lat_radius * cos_lon,
        lat_radius * sin_lon,
        ((1 - E_2) * partial_radius + ele) * sin_lat,
    )


def infer_nones(data):
    """Infer None values by linear interpolation."""
    none_count = 0
    last_good = None
    for index, value in enumerate(data):
        if value is None:
            none_count += 1
            continue
        if none_count:
            gap_size = none_count + 1
            for write_back in range(1, gap_size):
                if last_good is None:
                    data[index - write_back] = value
                else:
                    data[index - write_back] = (
                        value * (gap_size - write_back) + last_good * (write_back)
                    ) / gap_size
            none_count = 0
        last_good = value
    if none_count:
        if last_good is None:
            raise ValueError("Cannot interpolate from all Nones")
        for write_back in range(0, none_count + 1):
            data[index - write_back] = last_good
    return data


class Track:
    """A series of GPS points at given times."""

    def __init__(self, fields):
        self.fields = fields
        for essential in ("lat", "lon"):
            if essential not in self.fields or set(self.fields[essential]) == {None}:
                raise ValueError("Missing lat or lon in Track field")
            infer_nones(self.fields[essential])

        if "time" in self.fields:
            infer_nones(self.fields["time"])

        if self.has_altitude_data:
            elevation_data = self.fields["ele"]
            elevation_data = infer_nones(elevation_data)
        else:
            elevation_data = [0 for _ in range(len(self))]

        self.fields["x"] = []
        self.fields["y"] = []
        self.fields["z"] = []
        for point in range(len(self)):
            x, y, z = to_cartesian(
                self.fields["lat"][point],
                self.fields["lon"][point],
                elevation_data[point],
            )
            self.fields["x"].append(x)
            self.fields["y"].append(y)
            self.fields["z"].append(z)
        self.fields["dist_to_last"] = [None]
        for point in range(1, len(self)):
            self.fields["dist_to_last"].append(
                math.sqrt(
                    sum(
                        (self.fields[i][point] - self.fields[i][point - 1]) ** 2
                        for i in "xyz"
                    )
                )
            )
        # Calculate cumulative distances and speeds
        total_dist = 0
        self.fields["dist"] = [0]
        for point in range(1, len(self)):
            total_dist += self.fields["dist_to_last"][point]
            self.fields["dist"].append(total_dist)
        self.length = total_dist

        self.fields["speed"] = []
        for point_index in range(0, len(self)):
            relevant_points = [
                point_index + i for i in range(-SPEED_RANGE, SPEED_RANGE + 1)
            ]
            while relevant_points[0] < 0:
                relevant_points.pop(0)
            while relevant_points[-1] >= len(self):
                relevant_points.pop(-1)
            time_diff = (
                self.fields["time"][relevant_points[-1]]
                - self.fields["time"][relevant_points[0]]
            ).total_seconds()
            distance = sum(self.fields["dist_to_last"][p] for p in relevant_points[1:])
            if time_diff:
                self.fields["speed"].append(distance / time_diff)
            elif self.fields["speed"]:
                self.fields["speed"].append(self.fields["speed"][-1])
            else:
                self.fields["speed"].append(0)

    def __len__(self):
        return len(self.fields["lat"])

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
                for p in range(1, len(self.fields["ele"]))
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
