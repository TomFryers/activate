"""
Defines the activity list, which contains all of the user's real data.

This is where computation of summary values should be done.
"""
import datetime
import pickle
from dataclasses import dataclass

from activate.app import paths
from activate.core import activity, times, units


def from_disk():
    """Load an activity list from disk, if it exists."""
    try:
        with open(paths.SAVE, "rb") as f:
            return ActivityList(pickle.load(f))
    except FileNotFoundError:
        return ActivityList([])


@dataclass
class UnloadedActivity:
    name: str
    sport: str
    flags: dict
    start_time: datetime.datetime
    distance: float
    duration: float
    climb: float
    activity_id: int

    def load(self) -> activity.Activity:
        """Get the corresponding loaded Activity from disk."""
        with open(f"{paths.ACTIVITIES}/{self.activity_id}.pickle", "rb") as f:
            data = pickle.load(f)
        return activity.Activity(*data)

    @property
    def list_row(self):
        return [
            self.name,
            self.sport,
            self.start_time,
            units.DimensionValue(self.distance, "distance"),
        ]


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
        with open(paths.SAVE, "wb") as f:
            pickle.dump(self[:], f)

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

    def total_distance(self, activity_types, time_period, now, back=0):
        return sum(
            a.distance for a in self.filtered(activity_types, time_period, now, back)
        )

    def total_time(self, activity_types, time_period, now, back=0):
        return sum(
            (a.duration for a in self.filtered(activity_types, time_period, now, back)),
            datetime.timedelta(),
        )

    def total_climb(self, activity_types, time_period, now, back=0):
        return sum(
            a.climb for a in self.filtered(activity_types, time_period, now, back)
        )

    def total_activities(self, activity_types, time_period, now, back=0):
        return sum(1 for _ in self.filtered(activity_types, time_period, now, back))

    def get_progression_data(self, activity_types, time_period, now, key):
        """
        Get the activity dates, along with the total at that point.

        Filter out the wrong activity_types. Evaluate key for each
        activity, and get (dates, totals) in order.
        """
        time_period = time_period.casefold()
        if time_period == "all time":
            data = ([], [])
            total = 0
            valid_sorted = sorted(
                self.filtered(activity_types, time_period, now, 0),
                key=lambda x: x.start_time,
            )
            for a in valid_sorted:
                data[0].append(a.start_time)
                data[1].append(total)
                total += key(a)
                data[0].append(a.start_time + a.duration)
                data[1].append(total)

            return [data]

        # Other time periods
        result = []
        for back in range(5):
            data = ([times.start_of(now, time_period)], [0])
            total = 0
            valid_sorted = sorted(
                self.filtered(activity_types, time_period, now, back),
                key=lambda x: x.start_time,
            )
            for a in valid_sorted:
                data[0].append(times.to_this_period(now, a.start_time, time_period))
                data[1].append(total)
                total += key(a)
                data[0].append(
                    times.to_this_period(now, a.start_time + a.duration, time_period)
                )
                data[1].append(total)
            if back != 0:
                data[0].append(times.end_of(now, time_period))
                data[1].append(total)
            result.append(data)

        return result

    def __repr__(self):
        return f"<{self.__class__.__name__} {super().__repr__()} _activities={self._activities!r}>"
