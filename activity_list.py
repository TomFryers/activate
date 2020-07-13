import datetime

import activity

try:
    import cPickle as pickle
except ImportError:
    import pickle


SAVE_FILE = "activity_list.pickle"


def from_disk():
    """Load an activity list from disk, if it exists."""
    try:
        with open(SAVE_FILE, "rb") as f:
            return ActivityList(pickle.load(f))
    except FileNotFoundError:
        return ActivityList([])


class UnloadedActivity:
    def __init__(
        self, name, sport, flags, start_time, distance, duration, climb, activity_id
    ):
        self.name = name
        self.sport = sport
        self.flags = flags
        self.start_time = start_time
        self.distance = distance
        self.duration = duration
        self.climb = climb
        self.activity_id = activity_id

    def load(self) -> activity.Activity:
        """Get the corresponding loaded Activity from disk."""
        with open(f"{activity.DATA_DIR}/{self.activity_id}.pickle", "rb") as f:
            data = pickle.load(f)
        return activity.Activity(*data)

    @property
    def list_row(self):
        return [self.name, self.sport, self.start_time, (self.distance, "distance")]


class ActivityList(list):
    def __init__(self, activities):
        """Create a list of unloaded activities."""
        self._activities = {}
        self._links = {}
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

        This only stores the list data, not the actual activities or
        links.
        """
        with open(SAVE_FILE, "wb") as f:
            pickle.dump(self[:], f)

    def add_activity(self, new_activity, link):
        """
        Add a new activity with a link to it.

        Also saves the activity to disk.
        """
        self._links[link] = new_activity.activity_id
        self._activities[new_activity.activity_id] = new_activity
        self.append(new_activity.create_unloaded())
        new_activity.save()

    def from_link(self, link):
        """Retrieve an activity from a link."""
        return self.get_activity(self._links[link])

    def link(self, activity_, link):
        """Store a link to an activity."""
        self._links[link] = activity_.activity_id

    def update(self, activity_id, link):
        """Regenerate an unloaded activity from its loaded version."""
        for i, unloaded_activity in enumerate(self):
            if unloaded_activity.activity_id == activity_id:
                self[i] = self._activities[activity_id].create_unloaded()
                break
        self._links = dict(
            (link, v) if v == activity_id else (k, v) for k, v in self._links.items()
        )

    def filtered(self, activity_types):
        return (a for a in self if a.sport in activity_types)

    def total_distance(self, activity_types):
        return sum(a.distance for a in self.filtered(activity_types))

    def total_time(self, activity_types):
        return sum(
            (a.duration for a in self.filtered(activity_types)), datetime.timedelta()
        )

    def total_climb(self, activity_types):
        return sum(a.climb for a in self.filtered(activity_types))

    def total_activities(self, activity_types):
        return sum(1 for _ in self.filtered(activity_types))
