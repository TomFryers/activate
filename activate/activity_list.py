"""
Defines the activity list, which contains all of the user's real data.

This is where computation of summary values should be done.
"""
import dataclasses
import datetime
from collections import Counter
from typing import Optional

from activate import activity, serialise, times, units

LIST_FILENAME = "activity_list.json.gz"
ACTIVITIES_DIR_NAME = "activities"


def from_serial(serial, path):
    return ActivityList((UnloadedActivity(**a) for a in serial), path)


def from_disk(path):
    """Load an activity list from disk, if it exists."""
    try:
        return from_serial(serialise.load(path / LIST_FILENAME), path)
    except FileNotFoundError:
        return ActivityList([], path)


@dataclasses.dataclass
class UnloadedActivity:
    name: str
    sport: str
    flags: dict
    effort_level: Optional[int]
    start_time: datetime.datetime
    distance: float
    duration: float
    climb: float
    activity_id: str
    server: Optional[str] = None
    username: Optional[str] = None

    def load(self, path) -> activity.Activity:
        """Get the corresponding loaded Activity from disk."""
        return activity.Activity(**serialise.load(path / f"{self.activity_id}.json.gz"))

    @property
    def list_row(self):
        result = [
            self.name,
            self.sport,
            self.start_time,
            units.DimensionValue(self.distance, "distance"),
        ]
        if self.server is not None:
            result = [self.server, self.username] + result
        return result


class ActivityList(list):
    """A list of activities, which may be loaded."""

    def __init__(self, activities, path=None):
        """Create a list of unloaded activities."""
        self._activities = {}
        self.path = path
        super().__init__(activities)

    def by_id(self, activity_id):
        try:
            return next(a for a in self if a.activity_id == activity_id)
        except StopIteration as e:
            raise KeyError("No such activity_id") from e

    def provide_full_activity(self, activity_id, activity_):
        self._activities[activity_id] = activity_

    def get_activity(self, activity_id):
        """Get an activity from its activity_id."""
        if activity_id not in self._activities:
            if self.path is None:
                raise ValueError("Cannot load activity")
            self.provide_full_activity(
                activity_id,
                self.by_id(activity_id).load(self.path / ACTIVITIES_DIR_NAME),
            )
        return self._activities[activity_id]

    def serialised(self):
        return [dataclasses.asdict(a) for a in self]

    def save(self):
        """
        Store the activity list in a file.

        This only stores the list data, not the actual activities.
        """
        serialise.dump(self.serialised(), self.path / LIST_FILENAME, gz=True)

    def save_activity(self, activity_id):
        self.get_activity(activity_id).save(self.path / ACTIVITIES_DIR_NAME)

    def add_activity(self, new_activity):
        """
        Add a new activity.

        Also saves the activity to disk.
        """
        self._activities[new_activity.activity_id] = new_activity
        self.append(new_activity.unload(UnloadedActivity))
        new_activity.save(self.path / ACTIVITIES_DIR_NAME)

    def update(self, activity_id):
        """Regenerate an unloaded activity from its loaded version."""
        for i, unloaded_activity in enumerate(self):
            if unloaded_activity.activity_id == activity_id:
                self[i] = self._activities[activity_id].unload(UnloadedActivity)
                break

    def remove(self, activity_id):
        """Remove an activity from all parts of the ActivityList."""
        # Remove from main list
        for a in self:
            if a.activity_id == activity_id:
                super().remove(a)
        # Remove from loaded activities
        if activity_id in self._activities:
            del self._activities[activity_id]

    def filtered(self, activity_types, time_period, now, back=0):
        """
        Get an iterable of the matching activities.

        The activity types must match activity_types and they must have
        taken place in the correct time period. The values for
        time_period are "all time", "year", "month" and "week". A value
        of zero for back gives this year/month/week, 1 gives the
        previous, etc.
        """
        time_period = time_period.casefold()

        return (
            a
            for a in self
            if a.sport in activity_types
            and (
                time_period == "all time"
                or times.period_difference(now, a.start_time, time_period) == back
            )
        )

    def total_distance(self, activities):
        return sum(a.distance for a in activities)

    def total_time(self, activities):
        return sum((a.duration for a in activities), datetime.timedelta())

    def total_activities(self, activities):
        return sum(1 for _ in activities)

    def total_climb(self, activities):
        return sum(a.climb for a in activities if a.climb is not None)

    def eddington(self, activities, progress=lambda x: x) -> list:
        """Get a list of days sorted by distance done that day."""
        return sorted(
            sum(
                (
                    Counter(self.get_activity(a.activity_id).track.distance_in_days)
                    for a in progress(activities)
                ),
                Counter(),
            ).values(),
            reverse=True,
        )

    def get_progression_data(self, activity_types, time_period, now, key):
        """
        Get the activity dates, along with the total at that point.

        Filter out the wrong activity_types. Evaluate key for each
        activity, and get (dates, totals) in order.
        """
        time_period = time_period.casefold()
        if time_period == "all time":
            data = ([], [])
            total = None
            valid_sorted = sorted(
                self.filtered(activity_types, time_period, now, 0),
                key=lambda x: x.start_time,
            )
            for a in valid_sorted:
                value = key(a)
                if value is None:
                    continue
                if total is None:
                    total = value - value
                data[0].append(a.start_time)
                data[1].append(total)
                total += value
                data[0].append(a.start_time + a.duration)
                data[1].append(total)
            if total is not None:
                data[0].append(now)
                data[1].append(total)

            return (None, [data])

        # Other time periods
        # This is a bit of a hack: all dates are changed to around 1971
        # so that DateTimeAxis can eventually handle them
        periods = []
        result = []
        for back in range(5):
            start = times.start_of(times.EPOCH, time_period)
            data = ([start], [0])
            total = None
            valid_sorted = sorted(
                self.filtered(activity_types, time_period, now, back),
                key=lambda x: x.start_time,
            )
            if not valid_sorted:
                continue
            for a in valid_sorted:
                value = key(a)
                if value is None:
                    continue
                if total is None:
                    total = value - value
                data[0].append(start + times.since_start(a.start_time, time_period))
                data[1].append(total)
                total += value
                data[0].append(
                    start + times.since_start(a.start_time + a.duration, time_period)
                )
                data[1].append(total)
            if back != 0:
                data[0].append(times.end_of(times.EPOCH, time_period))
            else:
                data[0].append(times.EPOCH + times.since_start(now, time_period))
            data[1].append(total)
            result.append(data)
            periods.append(times.back_name(now, time_period, back))

        return (periods[::-1], result[::-1])

    def get_records(
        self, activity_types, time_period, now, distances, progress=lambda x: x
    ):
        records = {}
        activity_ids = {}
        for activity_ in progress(self.filtered(activity_types, time_period, now, 0)):
            for record in self.get_activity(activity_.activity_id).track.get_curve(
                distances
            )[0]:
                if record[0] not in records or records[record[0]][0] > record[1]:
                    records[record[0]] = record[1:] + (activity_.name,)
                    activity_ids[record[0]] = activity_.activity_id
        return (
            [(distance,) + record for distance, record in records.items()],
            activity_ids.values(),
        )

    def get_all_photos(self, activity_types, time_period, now):
        return (
            p
            for a in self.filtered(activity_types, time_period, now)
            for p in self.get_activity(a.activity_id).photos
        )

    def get_all_routes(self, activity_types, time_period, now, progress=lambda x: x):
        result = []
        for activity_ in progress(self.filtered(activity_types, time_period, now)):
            track = self.get_activity(activity_.activity_id).track
            if track.has_position_data:
                result.append(track.lat_lon_list)
        return result

    def get_matching(self, activity_, tolerance, progress=lambda x: x):
        matching = {activity_.activity_id}
        if not activity_.track.has_position_data:
            return matching
        for other_activity in progress(self):
            if other_activity.activity_id == activity_.activity_id or not (
                other_activity.sport == activity_.sport
                and other_activity.distance / 1.2
                < activity_.distance
                < other_activity.distance * 1.2
            ):
                continue
            if activity_.track.match(
                self.get_activity(other_activity.activity_id).track, tolerance
            ):
                matching.add(other_activity.activity_id)

        return matching

    def __repr__(self):
        return (
            f"<{self.__class__.__qualname__}"
            f" {super().__repr__()}"
            f" _activities={self._activities!r}>"
        )
