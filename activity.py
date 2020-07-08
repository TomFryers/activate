import random

import activity_list

try:
    import cPickle as pickle
except ImportError:
    import pickle


DATA_DIR = "activities"


def from_track(name, sport, track, filename):
    return Activity(name, sport, track, filename)


class Activity:
    def __init__(
        self,
        name,
        sport,
        track,
        original_name,
        start_time=None,
        distance=None,
        activity_id=None,
    ):
        self.name = name
        self.sport = sport
        self.track = track
        self.original_name = original_name
        if start_time is None:
            start_time = self.track.start_time
        self.start_time = start_time
        if distance is None:
            distance = self.track.length
        self.distance = distance
        if activity_id is None:
            self.activity_id = random.getrandbits(128)
        else:
            self.activity_id = activity_id

    @property
    def stats(self):
        return {
            "Distance": (self.distance, "distance"),
            "Elapsed Time": (self.track.elapsed_time, "time"),
            "Ascent": (self.track.ascent, "altitude")
            if self.track.has_altitude_data
            else "None",
            "Descent": (self.track.descent, "altitude")
            if self.track.has_altitude_data
            else "None",
            "Average Speed": (self.track.average_speed, "speed"),
            "Pace": (1 / self.track.average_speed, "pace"),
            "Max. Speed": (self.track.max_speed, "speed"),
            "Highest Point": (self.track.highest_point, "altitude")
            if self.track.has_altitude_data
            else "None",
        }

    def create_unloaded(self):
        return activity_list.UnloadedActivity(
            self.name, self.sport, self.start_time, self.distance, self.activity_id
        )

    @property
    def save_data(self):
        return (
            self.name,
            self.sport,
            self.track,
            self.original_name,
            self.start_time,
            self.distance,
            self.activity_id,
        )

    def save(self):
        with open(f"{DATA_DIR}/{self.activity_id}.pickle", "wb") as f:
            pickle.dump(self.save_data, f)
