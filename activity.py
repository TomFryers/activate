import pickle
import random

import activity_list
from units import DimensionValue

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
        flags=None,
        start_time=None,
        distance=None,
        activity_id=None,
        description="",
    ):
        self.name = name
        self.sport = sport
        self.track = track
        self.original_name = original_name
        if flags is None:
            self.flags = {}
        else:
            self.flags = flags

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
        self.description = description

    @property
    def stats(self):
        result = {}
        result["Distance"] = DimensionValue(self.distance, "distance")
        result["Elapsed Time"] = DimensionValue(self.track.elapsed_time, "time")
        if self.track.has_altitude_data:
            result["Ascent"] = DimensionValue(self.track.ascent, "altitude")
            result["Descent"] = DimensionValue(self.track.descent, "altitude")
        result["Average Speed"] = DimensionValue(self.track.average_speed, "speed")
        result["Pace"] = DimensionValue(1 / self.track.average_speed, "pace")
        result["Max. Speed"] = DimensionValue(self.track.max_speed, "speed")
        if self.track.has_altitude_data:
            result["Highest Point"] = DimensionValue(
                self.track.highest_point, "altitude"
            )
        if "heartrate" in self.track:
            result["Average HR"] = DimensionValue(
                self.track.average_heart_rate, "heartrate"
            )
        if "cadence" in self.track:
            result["Avg. Cadence"] = DimensionValue(
                self.track.average_cadence, "cadence"
            )
        if "power" in self.track:
            result["Average Power"] = DimensionValue(self.track.average_power, "power")
            result["Max. Power"] = DimensionValue(self.track.max_power, "power")
        return result

    @property
    def active_flags(self):
        return [k for k, v in self.flags.items() if v]

    def create_unloaded(self):
        return activity_list.UnloadedActivity(
            self.name,
            self.sport,
            self.flags,
            self.start_time,
            self.distance,
            self.track.elapsed_time,
            self.track.ascent,
            self.activity_id,
        )

    @property
    def save_data(self):
        return (
            self.name,
            self.sport,
            self.track,
            self.original_name,
            self.flags,
            self.start_time,
            self.distance,
            self.activity_id,
            self.description,
        )

    def save(self):
        with open(f"{DATA_DIR}/{self.activity_id}.pickle", "wb") as f:
            pickle.dump(self.save_data, f)
