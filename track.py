import math
import times
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
            # Write back interpolated values
            gap_size = none_count + 1
            for write_back in range(1, gap_size):
                # Nones at start
                if last_good is None:
                    data[index - write_back] = value
                # Nones in middle
                else:
                    data[index - write_back] = (
                        value * (gap_size - write_back) + last_good * (write_back)
                    ) / gap_size
            none_count = 0
        last_good = value
    if none_count:
        if last_good is None:
            raise ValueError("Cannot interpolate from all Nones")
        # Nones at end
        for write_back in range(0, none_count + 1):
            data[index - write_back] = last_good
    return data


class Track:
    """A series of GPS points at given times."""

    def __init__(self, fields):
        self.fields = fields
        for essential in ("lat", "lon"):
            if essential not in self.fields or set(self[essential]) == {None}:
                raise ValueError("Missing lat or lon in Track field")
            infer_nones(self[essential])

        if "time" in self.fields:
            infer_nones(self["time"])

        if not self.has_altitude_data:
            self["ele"] = [0 for _ in range(len(self))]
        self["ele"] = infer_nones(self["ele"])

    def __getitem__(self, field):
        try:
            return self.fields[field]
        except KeyError:
            if field in {"x", "y", "z"}:
                self.calculate_cartesian()
            elif field == "dist_to_last":
                self.calculate_dist_to_last()
            elif field == "dist":
                self.calculate_dist()
            elif field == "speed":
                self.calculate_speed()
            elif field in {"climb", "desc"}:
                self.calculate_climb_desc()
        return self.fields[field]

    def __setitem__(self, field, value):
        self.fields[field] = value

    def calculate_cartesian(self):
        """Calculate cartesian coordinates for each point"""
        self.fields["x"] = []
        self.fields["y"] = []
        self.fields["z"] = []
        for point in range(len(self)):
            x, y, z = to_cartesian(
                self["lat"][point], self["lon"][point], self["ele"][point],
            )
            self.fields["x"].append(x)
            self.fields["y"].append(y)
            self.fields["z"].append(z)

    def calculate_dist_to_last(self):
        """Calculate distances between adjacent points"""
        self.fields["dist_to_last"] = [None]
        for point in range(1, len(self)):
            self.fields["dist_to_last"].append(
                math.sqrt(
                    sum((self[i][point] - self[i][point - 1]) ** 2 for i in "xyz")
                )
            )

    def calculate_climb_desc(self):
        self.fields["climb"] = [None]
        self.fields["desc"] = [None]
        current = self["ele"][0]
        for point in range(1, len(self)):
            last = current
            current = self["ele"][point]
            if current > last:
                self.fields["climb"].append(current - last)
                self.fields["desc"].append(0)
            else:
                self.fields["desc"].append(last - current)
                self.fields["climb"].append(0)

    def calculate_dist(self):
        """Calculate cumulative distances"""
        total_dist = 0
        self.fields["dist"] = [0]
        for point in range(1, len(self)):
            total_dist += self["dist_to_last"][point]
            self.fields["dist"].append(total_dist)

    def calculate_speed(self):
        """Calculate speeds at each point"""
        speeds = []
        for point_index in range(0, len(self)):
            relevant_points = [
                point_index + i for i in range(-SPEED_RANGE, SPEED_RANGE + 1)
            ]
            while relevant_points[0] < 0:
                relevant_points.pop(0)
            while relevant_points[-1] >= len(self):
                relevant_points.pop(-1)
            time_diff = (
                self["time"][relevant_points[-1]] - self["time"][relevant_points[0]]
            ).total_seconds()
            distance = sum(self["dist_to_last"][p] for p in relevant_points[1:])
            if time_diff:
                speeds.append(distance / time_diff)
            elif speeds:
                speeds.append(speeds[-1])
            else:
                speeds.append(0)
        self["speed"] = speeds

    def __len__(self):
        return len(self["lat"])

    # Caching necessary to avoid fake elevation data
    @cached_property
    def has_altitude_data(self):
        return "ele" in self.fields

    @cached_property
    def lat_lon_list(self):
        return [[x, y] for x, y in zip(self["lat"], self["lon"])]

    @cached_property
    def ascent(self):
        if self.has_altitude_data:
            return sum(x for x in self["climb"] if x is not None)

    @cached_property
    def descent(self):
        if self.has_altitude_data:
            return sum(x for x in self["desc"] if x is not None)

    @cached_property
    def max_speed(self):
        return max(self["speed"])

    @cached_property
    def highest_point(self):
        return max(self["ele"])

    @property
    def start_time(self):
        return self["time"][0]

    @cached_property
    def elapsed_time(self):
        end_time = self["time"][-1]
        return end_time - self.start_time

    @cached_property
    def average_speed(self):
        duration = self.elapsed_time.total_seconds()
        return self.length / duration

    @cached_property
    def alt_graph(self):
        return list(zip((x / 1000 for x in self["dist"]), self["ele"]))

    @cached_property
    def speed_graph(self):
        return list(
            zip((x / 1000 for x in self["dist"]), (x * 3.6 for x in self["speed"]))
        )

    @property
    def length(self):
        return self["dist"][-1]

    @cached_property
    def splits(self, splitlength=1000):
        splits = []
        lasttime = None
        lastalt = None
        total_climb = 0
        for time, dist, alt, climb in zip(
            self["time"], self["dist"], self["ele"], self["climb"]
        ):
            if lasttime is None:
                lasttime = time
                lastalt = alt
            if dist // splitlength > len(splits):
                speed = 3.6 * splitlength / (time - lasttime).total_seconds()
                splits.append(
                    [
                        times.to_string(time - lasttime),
                        times.to_string(time - self.start_time),
                        (speed, f"{speed:.2f}"),
                        (alt - lastalt, str(round(alt - lastalt))),
                        (total_climb, str(round(total_climb))),
                    ]
                )
                total_climb = 0
                lasttime = None
            if climb is not None:
                total_climb += climb

        return splits
