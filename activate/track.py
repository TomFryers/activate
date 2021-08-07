"""Contains the Track class and functions for handling tracks."""
import math
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from itertools import tee
import bisect

from dtw import dtw

from activate import geometry, times
from activate.units import DimensionValue

SPEED_RANGE = 1

FIELD_DIMENSIONS = {
    "lat": "latlon",
    "lon": "latlon",
    "ele": "altitude",
    "height_change": "altitude",
    "vertical_speed": "vertical_speed",
    "climb": "altitude",
    "desc": "altitude",
    "gradient": None,
    "angle": "angle",
    "time": "time",
    "speed": "speed",
    "dist": "distance",
    "dist_to_last": "distance",
    "cadence": "cadence",
    "heartrate": "heartrate",
    "power": "power",
}

NON_SAVED = {"vertical_speed", "climb", "desc", "gradient", "angle"}


def lerp(value1, value2, ratio):
    """
    Interpolate between value1 and value2.

    lerp(x, y, 0) = x
    lerp(x, y, 0.5) = (x + y) / 2
    lerp(x, y, 1) = y
    """
    return value1 + ratio * (value2 - value1)


def pairs(iterator):
    """Return pairs of adjacent items."""
    firsts, seconds = tee(iterator, 2)
    next(seconds)
    return zip(firsts, seconds)


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
                    data[index - write_back] = lerp(
                        value, last_good, write_back / gap_size
                    )

            none_count = 0
        last_good = value
    if not none_count:
        return data
    # Nones at end
    if last_good is None:
        raise ValueError("Cannot interpolate from all Nones")
    for write_back in range(none_count + 1):
        data[index - write_back] = last_good
    return data


def get_nearby_indices(length, position, number=1) -> range:
    """
    Return numbers around position, with at most number either side.

    If position is too close to 0 or length, the excess points are
    removed.
    """
    return range(max(position - number, 0), min(position + number + 1, length))


try:
    from math import dist
except ImportError:

    def dist(point1, point2):
        return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(point1, point2)))


def enumerate_from(list_, point):
    return enumerate(list_[point:], point)


@dataclass
class ManualTrack:
    """A manual track with a few basic values."""

    start_time: datetime
    length: float
    ascent: float
    elapsed_time: timedelta

    has_altitude_data = False
    has_position_data = False
    manual = True

    def average(self, field):
        if field == "speed":
            return self.length / self.elapsed_time.total_seconds()
        raise AttributeError(f"{self.__class__.__qualname__} has no average {field}")

    @property
    def save_data(self):
        result = asdict(self)
        result["manual"] = True
        return result

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
            if essential in self.fields:
                with suppress(ValueError):
                    infer_nones(self[essential])

        if "time" in self.fields:
            infer_nones(self["time"])

        self["ele"] = (
            infer_nones(self["ele"])
            if self.has_altitude_data
            else [0 for _ in range(len(self))]
        )

    def __getitem__(self, field):
        try:
            return self.fields[field]
        except KeyError:
            if field == "dist_to_last":
                self.calculate_dist_to_last()
            elif field == "dist":
                self.calculate_dist()
            elif field == "speed":
                self.calculate_speed()
            elif field in {"climb", "desc"}:
                self.calculate_climb_desc()
            elif field == "height_change":
                self.calculate_height_change()
            elif field == "vertical_speed":
                self.calculate_vertical_speed()
            elif field == "gradient":
                self.calculate_gradient()
            elif field == "angle":
                self.calculate_angle()
        return self.fields[field]

    def __setitem__(self, field, value):
        self.fields[field] = value

    def __contains__(self, field):
        if field in {"dist_to_last", "dist"}:
            return "dist" in self or "dist_to_last" in self or self.has_position_data
        if field in {
            "climb",
            "desc",
            "height_change",
            "vertical_speed",
            "gradient",
            "angle",
        }:
            return self.has_altitude_data
        return field in self.fields

    @property
    @lru_cache(128)
    def temporal_resolution(self):
        return min(y - x for x, y in pairs(self["time"])).total_seconds()

    @property
    @lru_cache(128)
    def xyz(self):
        return [
            geometry.to_cartesian(*point)
            for point in zip(self["lat"], self["lon"], self["ele"])
        ]

    def calculate_dist_to_last(self):
        """Calculate distances between adjacent points."""
        self.fields["dist_to_last"] = [None]
        if "dist" in self.fields:
            for point in range(1, len(self)):
                relevant = self.fields["dist"][point - 1 : point + 1]
                self.fields["dist_to_last"].append(
                    None if None in relevant else relevant[1] - relevant[0]
                )
        else:
            self.fields["dist_to_last"] += [dist(*x) for x in pairs(self.xyz)]

    def calculate_climb_desc(self):
        self.fields["climb"] = [None]
        self.fields["desc"] = [None]
        for height_change in self["height_change"][1:]:
            # Not using max in order to have integers instead of floats,
            # since max(0, 0.0) is 0.0. It's common to have a height
            # difference of 0.0 in tracks, because altimeters are not
            # very sensitive.
            self.fields["climb"].append(0 if height_change <= 0 else height_change)
            self.fields["desc"].append(0 if height_change >= 0 else -height_change)

    def calculate_dist(self):
        """Calculate cumulative distances."""
        total_dist = 0
        new_dist = [0]
        for dist in self["dist_to_last"][1:]:
            total_dist += dist
            new_dist.append(total_dist)
        self.fields["dist"] = new_dist

    def calculate_speed(self):
        """Calculate speeds at each point."""
        speeds = []
        for point_index in range(len(self)):
            relevant_points = get_nearby_indices(
                len(self), point_index, number=SPEED_RANGE
            )
            time_diff = (
                self["time"][relevant_points[-1]] - self["time"][relevant_points[0]]
            ).total_seconds()
            distance = sum(
                self["dist_to_last"][p]
                for p in relevant_points[1:]
                if self["dist_to_last"][p] is not None
            )
            if time_diff:
                speeds.append(distance / time_diff)
            elif speeds:
                speeds.append(speeds[-1])
            else:
                speeds.append(0)
        self["speed"] = speeds

    def calculate_height_change(self):
        """Calculate differences in elevation between adjacent points."""
        self.fields["height_change"] = [None] + [y - x for x, y in pairs(self["ele"])]

    def calculate_vertical_speed(self):
        """Calculate vertical speed at each point."""
        self.fields["vertical_speed"] = [None]
        for point in range(1, len(self)):
            height_change = self["height_change"][point]
            time = self["time"][point]
            last_time = self["time"][point - 1]
            if None in {height_change, time, last_time}:
                self.fields["vertical_speed"].append(None)
            else:
                self.fields["vertical_speed"].append(
                    height_change / (time - last_time).total_seconds()
                )

    def calculate_gradient(self):
        """Calculate the gradient at each point."""
        self.fields["gradient"] = [None]
        for dist, height_change in list(
            zip(self["dist_to_last"], self["height_change"])
        )[1:]:
            self.fields["gradient"].append(
                None if dist in {None, 0} else height_change / dist
            )

    def calculate_angle(self):
        """Calculate the angle of inclination at each point."""
        self.fields["angle"] = [
            None if g is None else math.atan(g) for g in self["gradient"]
        ]

    def __len__(self):
        return len(next(iter(self.fields.values())))

    @lru_cache(128)
    def without_nones(self, field):
        return [v for v in self[field] if v is not None]

    @lru_cache(128)
    def average(self, field):
        """Get the mean value of a field, ignoring missing values."""
        if field == "speed":
            return self.length / self.elapsed_time.total_seconds()

        valid = list(self.without_nones(field))
        return sum(valid) / len(valid)

    @lru_cache(128)
    def maximum(self, field):
        """Get the maximum value of a field, ignoring missing values."""
        return max(self.without_nones(field))

    # Caching necessary to avoid fake elevation data
    @property
    @lru_cache(128)
    def has_altitude_data(self):
        return "ele" in self.fields

    @property
    @lru_cache(128)
    def has_position_data(self):
        return "lat" in self.fields and "lon" in self.fields

    @property
    @lru_cache(128)
    def lat_lon_list(self):
        return [[x, y] for x, y in zip(self["lat"], self["lon"])]

    def part_lat_lon_list(self, min_dist, max_dist):
        track = []
        for dist, lat, lon in zip(self["dist"], self["lat"], self["lon"]):
            if dist is None or dist < min_dist:
                continue
            if dist >= max_dist:
                return track
            track.append([lat, lon])
        return track

    @property
    @lru_cache(128)
    def ascent(self):
        if self.has_altitude_data:
            return sum(self.without_nones("climb"))

    @property
    @lru_cache(128)
    def descent(self):
        if self.has_altitude_data:
            return sum(self.without_nones("desc"))

    @property
    def start_time(self):
        return self["time"][0]

    @property
    @lru_cache(128)
    def elapsed_time(self) -> timedelta:
        end_time = self["time"][-1]
        return end_time - self.start_time

    @property
    @lru_cache(128)
    def moving_time(self) -> timedelta:
        total_time = timedelta(0)
        last_distance = 0
        last_time = self.start_time
        for distance, time in zip(self["dist"][1:], self["time"][1:]):
            if distance is None:
                continue
            time_difference = time - last_time
            if not time_difference:
                continue
            distance_difference = distance - last_distance
            if distance_difference < 1:
                continue
            if distance_difference / time_difference.total_seconds() > 0.2:
                total_time += time_difference
            elif distance < last_distance:
                raise ValueError("Distance increase")
            last_distance = distance
            last_time = time

        return total_time

    @property
    @lru_cache(128)
    def average_speed_moving(self):
        return self.length / self.moving_time.total_seconds()

    @property
    @lru_cache(128)
    def distance_in_days(self) -> dict:
        if self.start_time.date() == self["time"][-1].date():
            return {self.start_time.date(): self.length}
        last_time = self.start_time
        last_date = last_time.date()
        totals = {last_date: 0}

        for dist_to_last, time in zip(self["dist_to_last"][1:], self["time"][1:]):
            if dist_to_last is None:
                continue
            date = time.date()
            if date == last_date:
                totals[last_date] += dist_to_last
            else:
                speed = dist_to_last / (time - last_time).total_seconds()
                totals[last_date] += (
                    speed * (times.end_of(last_time, "day") - last_time).total_seconds()
                )
                for days in range(1, (date - last_date).days):
                    day = last_date + timedelta(days)
                    totals[day] = speed * timedelta(days=1)
                totals[date] = (
                    speed * (time - times.start_of(time, "day")).total_seconds()
                )
                last_date = date

            last_time = time
        return totals

    def lat_lng_from_distance(self, distance):
        distances = self.without_nones("dist")
        point0 = bisect.bisect(distances, distance)
        try:
            point1 = next(
                i for i, d in enumerate_from(distances, point0) if d > distance
            )
        except StopIteration:
            return None
        point0 -= 1
        dist0 = distances[point0]
        dist1 = distances[point1]
        lat0 = self["lat"][point0]
        lon0 = self["lon"][point0]
        if dist0 == dist1:
            return (lat0, lon0)
        lat1 = self["lat"][point1]
        lon1 = self["lon"][point1]
        ratio = (distance - dist0) / (dist1 - dist0)
        return (lerp(lat0, lat1, ratio), lerp(lon0, lon1, ratio))

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
        for time, distance, alt, climb in zip(
            self["time"], self["dist"], self["ele"], self["climb"]
        ):
            if lasttime is None:
                lasttime = time
                lastalt = alt
            if distance is None:
                continue
            if distance // splitlength > len(splits):
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
        """Get the curve and curve table for an activity."""
        table_distances = [x for x in table_distances if x <= self.length][::-1]
        time_values = [t.timestamp() for t in self["time"]]

        bests = []
        point_indices = []
        for distance in table_distances:
            last_point = next(
                i for i, d in enumerate(self["dist"]) if d is not None and d > distance
            )
            best = time_values[last_point] - self.start_time.timestamp()
            first_point = 0
            point = (first_point, last_point)
            for last_point, last_dist in enumerate_from(self["dist"], last_point + 1):
                if last_dist is None:
                    continue
                last_good_first_point = first_point
                for first_point, first_dist in enumerate_from(
                    self["dist"], first_point
                ):
                    if first_dist is None:
                        continue
                    if last_dist - first_dist >= distance:
                        last_good_first_point = first_point
                    else:
                        break
                first_point = last_good_first_point
                time_taken = time_values[last_point] - time_values[first_point]
                if time_taken < best:
                    best = time_taken
                    point = (first_point, last_point)
            bests.append(best)
            point_indices.append(point)
            if best == self.temporal_resolution:
                break
        while len(point_indices) < len(table_distances):
            point_indices.append(point_indices[-1])
            bests.append(bests[-1])

        point_indices = point_indices[::-1]
        bests = bests[::-1]
        table_distances = table_distances[::-1]

        speeds = [
            distance / time if time else 0
            for distance, time in zip(table_distances, bests)
        ]
        bests_table = [
            (
                DimensionValue(distance, "distance"),
                DimensionValue(timedelta(seconds=time), "time"),
                DimensionValue(speed, "speed"),
            )
            for distance, time, speed in zip(table_distances, bests, speeds)
        ]
        return (
            bests_table,
            ((table_distances, "distance"), (speeds, "speed")),
            point_indices,
        )

    def match(self, other, tolerance=40):
        return (
            dtw(self.xyz, other.xyz, distance_only=True).normalizedDistance < tolerance
        )

    def max_point(self, stat):
        point = None
        maximum = float("-inf")
        for index, value in enumerate(self[stat]):
            if value is not None and value > maximum:
                maximum = value
                point = index
        return point

    @property
    def save_data(self):
        return {
            key: value for key, value in self.fields.items() if key not in NON_SAVED
        }
