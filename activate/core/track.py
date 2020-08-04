"""Contains the Track class and functions for handling tracks."""
import datetime
import math
from dataclasses import dataclass
from functools import cached_property, lru_cache

from activate.core import geometry, times
from activate.core.units import DimensionValue

SPEED_RANGE = 1

FIELD_DIMENSIONS = {
    "lat": "latlon",
    "lon": "latlon",
    "ele": "altitude",
    "climb": "altitude",
    "desc": "altitude",
    "time": "time",
    "speed": "speed",
    "dist": "distance",
    "dist_to_last": "distance",
    "cadence": "cadence",
    "heartrate": "heartrate",
    "power": "power",
    "x": "distance",
    "y": "distance",
    "z": "distance",
}


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


def get_nearby_indices(length, position, number=1) -> list:
    """
    Return numbers around position, with at most number either side.

    If position is too close to 0 or length, the excess points are
    removed.
    """
    relevant_points = [position + i for i in range(-number, number + 1)]
    while relevant_points[0] < 0:
        relevant_points.pop(0)
    while relevant_points[-1] >= length:
        relevant_points.pop(-1)
    return relevant_points


@dataclass
class ManualTrack:
    start_time: datetime.datetime
    length: float
    ascent: float
    elapsed_time: datetime.timedelta

    has_altitude_data = False
    has_position_data = False
    manual = True

    def average(self, field):
        if field == "speed":
            return self.length / self.elapsed_time.total_seconds()
        raise AttributeError(f"{self.__class__.__name__} has no average {field}")

    def __contains__(self, _):
        return False


class Track:
    """
    A series of GPS points at given times.

    A track is considered to be purely a sequence of GPS points, with
    extra data for each point. For more metadata such as a name or
    description, the Track should be wrapped in an Activity.

    Some tracks (those representing pool swims) have no position data.
    """

    manual = False

    def __init__(self, fields):
        self.fields = fields
        for essential in ("lat", "lon"):
            if essential in self.fields and set(self[essential]) != {None}:
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

    def __contains__(self, field):
        if field in self.fields.keys():
            return True
        if field in {"x", "y", "z"}:
            return self.has_position_data
        if field in {"dist_to_last", "dist"}:
            return "dist" in self or "dist_to_last" in self or self.has_position_data
        if field in {"climb", "desc"}:
            return self.has_altitude_data
        return False

    def calculate_cartesian(self):
        """Calculate cartesian coordinates for each point"""
        self.fields["x"] = []
        self.fields["y"] = []
        self.fields["z"] = []
        for point in range(len(self)):
            x, y, z = geometry.to_cartesian(
                self["lat"][point], self["lon"][point], self["ele"][point],
            )
            self.fields["x"].append(x)
            self.fields["y"].append(y)
            self.fields["z"].append(z)

    def calculate_dist_to_last(self):
        """Calculate distances between adjacent points"""
        self.fields["dist_to_last"] = [None]
        if "dist" in self.fields:
            self.fields["dist_to_last"] += [
                self.fields["dist"][i] - self.fields["dist"][i - 1]
                for i in range(1, len(self))
            ]
        else:
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
        new_dist = [0]
        for point in range(1, len(self)):
            total_dist += self["dist_to_last"][point]
            new_dist.append(total_dist)
        self.fields["dist"] = new_dist

    def calculate_speed(self):
        """Calculate speeds at each point"""
        speeds = []
        for point_index in range(0, len(self)):
            relevant_points = get_nearby_indices(
                len(self), point_index, number=SPEED_RANGE
            )
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
        return len(next(iter(self.fields.values())))

    def without_nones(self, field):
        return (v for v in self[field] if v is not None)

    @lru_cache
    def average(self, field):
        """Get the mean value of a field, ignoring missing values."""
        if field == "speed":
            duration = self.elapsed_time.total_seconds()
            return self.length / duration

        valid = list(self.without_nones(field))
        return sum(valid) / len(valid)

    @lru_cache
    def maximum(self, field):
        """Get the maximum value of a field, ignoring missing values."""
        return max(self.without_nones(field))

    # Caching necessary to avoid fake elevation data
    @cached_property
    def has_altitude_data(self):
        return "ele" in self.fields

    @cached_property
    def has_position_data(self):
        return "lat" in self.fields and "lon" in self.fields

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

    @property
    def start_time(self):
        return self["time"][0]

    @cached_property
    def elapsed_time(self):
        end_time = self["time"][-1]
        return end_time - self.start_time

    def graph(self, y_data, x_data="dist") -> tuple:
        """Get x and y data as (data, dimension) tuples."""
        return (
            (self[x_data], FIELD_DIMENSIONS[x_data]),
            (self[y_data], FIELD_DIMENSIONS[y_data]),
        )

    @property
    def length(self):
        return next(x for x in reversed(self["dist"]) if x is not None)

    def splits(self, splitlength=1000) -> list:
        """
        Split an activity into splits, with per-split data.

        Each split is a list in the format
        [lap, split, speed, net climb, total climb].
        """
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
            if dist is None:
                continue
            if dist // splitlength > len(splits):
                speed = splitlength / (time - lasttime).total_seconds()
                splits.append(
                    [
                        DimensionValue(time - lasttime, "time"),
                        DimensionValue(time - self.start_time, "time"),
                        DimensionValue(speed, "speed"),
                        DimensionValue(alt - lastalt, "altitude"),
                        DimensionValue(total_climb, "altitude"),
                    ]
                )
                total_climb = 0
                lasttime = None
            if climb is not None:
                total_climb += climb

        return splits

    def get_zone_durations(self, zones, field="speed", count_field="time"):
        """
        Get durations for the zones graph.

        Between all zones values, calculate the total amount of
        count_field at each point where field is within the range given
        by that pair of zones values. The zones must be sorted in
        ascending order.
        """
        buckets = {z: 0 for z in zones}
        for point in range(len(self)):
            # Work out the amount of count_field at the point
            nearby_points = get_nearby_indices(len(self), point)
            duration = (
                self[count_field][nearby_points[-1]]
                - self[count_field][nearby_points[0]]
            ) / 2
            duration = times.to_number(duration)

            # Add it to the correct bucket
            value = self[field][point]
            if value is None:
                continue
            for zone in zones[::-1]:
                if value > zone:
                    buckets[zone] += duration
                    break

        return buckets

    def get_curve(self, table_distances):
        table_distances = [x for x in table_distances if x <= self.length]
        distance_values = []
        time_values = []
        for dist, time in zip(self["dist"], self["time"]):
            if dist is not None:
                distance_values.append(dist)
                time_values.append(time)

        bests = {}
        for distance in table_distances:
            for last_point in range(len(distance_values)):
                if distance_values[last_point] > distance:
                    break
            bests[distance] = (
                time_values[last_point] - self.start_time
            ).total_seconds()
            first_point = 0
            while last_point < len(distance_values) - 1:
                last_point += 1
                while True:
                    dist = distance_values[last_point] - distance_values[first_point]
                    if dist < distance:
                        break
                    first_point += 1
                first_point -= 1
                time_taken = (
                    time_values[last_point] - time_values[first_point]
                ).total_seconds()
                if time_taken < bests[distance] and first_point > 0:
                    bests[distance] = time_taken

        speeds = [distance / bests[distance] for distance in bests]
        bests_table = [
            (
                DimensionValue(distance, "distance"),
                DimensionValue(datetime.timedelta(seconds=bests[distance]), "time"),
                DimensionValue(distance / bests[distance], "speed"),
            )
            for distance in bests
        ]
        return (
            bests_table,
            ((list(bests.keys()), "distance"), (speeds, "speed")),
        )
