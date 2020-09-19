import random
import shutil

from activate.core import serialise
from activate.core import track as track_
from activate.core.units import DimensionValue


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
        photos=None,
        server=None,
        username=None,
    ):
        self.name = name
        self.sport = sport
        if isinstance(track, dict):
            self.track = track_.Track(track)
        else:
            self.track = track
        self.original_name = original_name
        self.server = server
        self.username = username
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
        if photos is None:
            self.photos = []
        else:
            self.photos = photos

    @property
    def stats(self):
        result = {}
        result["Distance"] = DimensionValue(self.distance, "distance")
        result["Elapsed Time"] = DimensionValue(self.track.elapsed_time, "time")
        if self.track.has_altitude_data:
            result["Ascent"] = DimensionValue(self.track.ascent, "altitude")
            result["Descent"] = DimensionValue(self.track.descent, "altitude")
        average_speed = self.track.average("speed")
        if average_speed > 0:
            result["Average Speed"] = DimensionValue(average_speed, "speed")
            result["Pace"] = DimensionValue(1 / average_speed, "pace")
        if not self.track.manual:
            result["Max. Speed"] = DimensionValue(self.track.maximum("speed"), "speed")
        if self.track.has_altitude_data:
            result["Highest Point"] = DimensionValue(
                self.track.maximum("ele"), "altitude"
            )
        if "heartrate" in self.track:
            result["Average HR"] = DimensionValue(
                self.track.average("heartrate"), "heartrate"
            )
        if "cadence" in self.track:
            result["Avg. Cadence"] = DimensionValue(
                self.track.average("cadence"), "cadence"
            )
        if "power" in self.track:
            result["Average Power"] = DimensionValue(
                self.track.average("power"), "power"
            )
            result["Max. Power"] = DimensionValue(self.track.maximum("power"), "power")
        return result

    @property
    def active_flags(self):
        return [k for k, v in self.flags.items() if v]

    def unload(self, unloaded_class):
        return unloaded_class(
            self.name,
            self.sport,
            self.flags,
            self.start_time,
            self.distance,
            self.track.elapsed_time,
            self.track.ascent,
            self.activity_id,
            self.server,
            self.username,
        )

    @property
    def save_data(self):
        return {
            "name": self.name,
            "sport": self.sport,
            "track": self.track.save_data,
            "original_name": self.original_name,
            "flags": self.flags,
            "start_time": self.start_time,
            "distance": self.distance,
            "activity_id": self.activity_id,
            "description": self.description,
            "photos": self.photos,
            "server": self.server,
            "username": self.username,
        }

    def save(self, path):
        serialise.dump(self.save_data, f"{path}{self.activity_id}.json.gz", gz=True)

    def export_original(self, filename):
        shutil.copy2(self.original_name, filename)
