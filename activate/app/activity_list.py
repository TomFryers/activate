"""
Defines the activity list, which contains all of the user's real data.

This is where computation of summary values should be done.
"""
import dataclasses
import datetime

from activate.app import paths
from activate.core import activity, serialise, times, units


def from_disk():
    """Load an activity list from disk, if it exists."""
    try:
        return ActivityList(UnloadedActivity(**a) for a in serialise.load(paths.SAVE))
    except FileNotFoundError:
        return ActivityList([])


@dataclasses.dataclass
class UnloadedActivity:
    name: str
    sport: str
    flags: dict
    start_time: datetime.datetime
    distance: float
    duration: float
    climb: float
    activity_id: int
    server: str = None
    username: str = None

    def load(self) -> activity.Activity:
        """Get the corresponding loaded Activity from disk."""
        return activity.Activity(
            **serialise.load(f"{paths.ACTIVITIES}/{self.activity_id}.json.gz")
        )

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

    def __init__(self, activities):
        """Create a list of unloaded activities."""
        self._activities = {}
        super().__init__(activities)

    def get_activity(self, activity_id):
        """Get an activity from its activity_id."""
        if activity_id not in self._activities:
            for unloaded_activity in self:
                if unloaded_activity.activity_id == activity_id:
                    self._activities[activity_id] = unloaded_activity.load()
        return self._activities[activity_id]

    def save(self):
        """
        Store the activity list in a file.

        This only stores the list data, not the actual activities.
        """
        serialise.dump([dataclasses.asdict(a) for a in self], paths.SAVE, gz=True)

    def add_activity(self, new_activity):
        """
        Add a new activity.

        Also saves the activity to disk.
        """
        self._activities[new_activity.activity_id] = new_activity
        self.append(new_activity.unload(UnloadedActivity))
        new_activity.save(paths.ACTIVITIES)

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
                data[1].append(total)
            else:
                data[0].append(times.EPOCH + times.since_start(now, time_period))
                data[1].append(total)
            result.append(data)
            periods.append(times.back_name(now, time_period, back))

        return (periods[::-1], result[::-1])

    def get_records(self, activity_types, time_period, now, distances):
        records = {}
        activity_ids = {}
        for activity_ in self.filtered(activity_types, time_period, now, 0):
            for record in activity_.load().track.get_curve(distances)[0]:
                if record[0] not in records or records[record[0]][0] > record[1]:
                    records[record[0]] = record[1:] + (activity_.name,)
                    activity_ids[record[0]] = activity_.activity_id
        return (
            [(distance,) + record for distance, record in records.items()],
            activity_ids.values(),
        )

    def get_all_photos(self, activity_types, time_period, now):
        return [
            p
            for a in self.filtered(activity_types, time_period, now)
            for p in a.load().photos
        ]

    def __repr__(self):
        return f"<{self.__class__.__name__} {super().__repr__()} _activities={self._activities!r}>"
