import load_activity


def from_track(name, track, filename):
    return Activity(name, track, filename)


class Activity:
    def __init__(self, name, track, filename, start_time=None, distance=None):
        self.name = name
        self._track = track
        self.filename = filename
        if start_time is None:
            start_time = self.track.start_time
        self.start_time = start_time
        if distance is None:
            distance = self.track.length
        self.distance = distance

    @property
    def track(self):
        if self._track is None:
            self._track = load_activity.load(self.filename)[1]
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
        return [self.name, self.start_time, (self.distance, "distance")]

    def cache(self):
        return {self.filename: (self.name, self.start_time, self.distance)}
