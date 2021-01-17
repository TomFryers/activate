import shutil
from uuid import uuid4

from activate import serialise
from activate import track as track_
from activate.units import DimensionValue


def from_track(name, sport, track, filename):
    return Activity(name, sport, track, filename)


def none_default(value, default):
    """Return default if value is None else value."""
    return default if value is None else value


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
        self.flags = none_default(flags, {})
        self.start_time = none_default(start_time, self.track.start_time)
        self.distance = none_default(distance, self.track.length)
        self.activity_id = none_default(activity_id, uuid4())
        self.description = description
        self.photos = none_default(photos, [])

    @property
    def stats(self):
        result = {}
        result["Distance"] = DimensionValue(self.distance, "distance")
        result["Elapsed Time"] = DimensionValue(self.track.elapsed_time, "time")
        if self.track.moving_time < self.track.elapsed_time:
            result["Moving Time"] = DimensionValue(self.track.moving_time, "time")
        if self.track.has_altitude_data:
            result["Ascent"] = DimensionValue(self.track.ascent, "altitude")
            result["Descent"] = DimensionValue(self.track.descent, "altitude")
        average_speed = self.track.average("speed")
        if average_speed > 0:
            average_speed_moving = self.track.average_speed_moving
            if average_speed_moving / average_speed < 1.01:
                average_speed_moving = None
            result["Average Speed"] = DimensionValue(average_speed, "speed")
            if average_speed_moving is not None:
                result["Mov. Av. Speed"] = DimensionValue(average_speed_moving, "speed")
            result["Pace"] = DimensionValue(1 / average_speed, "pace")
            if average_speed_moving is not None:
                result["Pace (mov.)"] = DimensionValue(1 / average_speed_moving, "pace")
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
        serialise.dump(self.save_data, path / f"{self.activity_id}.json.gz", gz=True)

    def export_original(self, filename):
        shutil.copy2(self.original_name, filename)
