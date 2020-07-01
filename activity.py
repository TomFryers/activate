import load_activity
import times

import datetime


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
        pace = 1000 / self.track.average_speed
        return {
            "Distance": (self.distance / 1000, f"{self.distance / 1000:.2f}"),
            "Elapsed Time": times.to_string(self.track.elapsed_time),
            "Ascent": (self.track.ascent, str(round(self.track.ascent)))
            if self.track.has_altitude_data
            else "None",
            "Descent": (self.track.descent, str(round(self.track.descent)))
            if self.track.has_altitude_data
            else "None",
            "Average Speed": (
                self.track.average_speed * 3.6,
                f"{self.track.average_speed * 3.6:.2f}",
            ),
            "Pace": (pace, times.to_string(datetime.timedelta(seconds=round(pace)))),
            "Max. Speed": (
                self.track.max_speed * 3.6,
                f"{self.track.max_speed * 3.6:.1f}",
            ),
            "Highest Point": (
                self.track.highest_point,
                str(round(self.track.highest_point)),
            )
            if self.track.has_altitude_data
            else "None",
        }

    @property
    def list_row(self):
        return [
            self.name,
            str(self.start_time),
            (self.distance / 1000, f"{self.distance / 1000:.2f}"),
        ]

    def cache(self):
        return {self.filename: (self.name, self.start_time, self.distance)}
