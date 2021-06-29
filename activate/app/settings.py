"""Contains a class holding current user settings."""
import dataclasses
from contextlib import suppress
from typing import Optional

from activate import serialise, units
from activate.app import connect, paths

DEFAULTS = {
    "tiles": None,
    "map_speed": 0.0,
    "unit_system": units.DEFAULT,
    "servers": [],
    "custom_units": {},
    "cookie": None,
}


def load_settings():
    """Load settings from a configuration file."""
    settings_data = DEFAULTS.copy()
    with suppress(FileNotFoundError):
        settings_data.update(serialise.load(paths.SETTINGS))

    settings_data["servers"] = [connect.Server(**s) for s in settings_data["servers"]]
    return Settings(**settings_data)


@dataclasses.dataclass
class Settings:
    """A settings configuration."""

    tiles: Optional[str]
    map_speed: float
    unit_system: str
    custom_units: dict
    servers: list
    cookie: Optional[str]

    def save(self):
        """Save settings to a configuration file."""
        serialise.dump(dataclasses.asdict(self), paths.SETTINGS, readable=True)

    def copy_from(self, other):
        for field in dataclasses.fields(self):
            setattr(self, field.name, getattr(other, field.name))
