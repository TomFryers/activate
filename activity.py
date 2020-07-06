import random

import load_activity

try:
    import cPickle as pickle
except ImportError:
    import pickle


def from_track(name, sport, track, filename):
    return Activity(name, sport, track, filename)


class Activity:
    def __init__(
        self,
        name,
        sport,
        track,
        filename,
        start_time=None,
        distance=None,
        flags=None,
        activity_id=None,
    ):
        self.name = name
        self.sport = sport
        self._track = track
        self.filename = filename
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
    def track(self):
        if self._track is None:
            self._track = load_activity.load(self.filename)[2]
        return self._track

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

    @property
    def list_row(self):
        return [self.name, self.sport, self.start_time, (self.distance, "distance")]

    def cache(self):
        return {
            self.activity_id: (
                self.name,
                self.filename,
                self.sport,
                self.start_time,
                self.distance,
            )
        }

    @property
    def save_data(self):
        return (self.activity_id, self.name, self.sport)

    def save(self, directory):
        with open(f"{directory}/{self.activity_id}.pickle", "wb") as f:
            pickle.dump(self.save_data, f)
