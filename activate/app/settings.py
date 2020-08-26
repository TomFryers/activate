"""Contains a class holding current user settings."""
import dataclasses

from activate.app import connect, paths
from activate.core import serialise, units

DEFAULTS = {"unit_system": units.DEFAULT, "servers": []}


def load_settings():
    """Load settings from a configuration file."""
    settings_data = DEFAULTS.copy()
    try:
        settings_data.update(serialise.load(paths.SETTINGS))
    except FileNotFoundError:
        pass

    settings_data["servers"] = [connect.Server(**s) for s in settings_data["servers"]]
    return Settings(**settings_data)


@dataclasses.dataclass
class Settings:
    """A settings configuration"""

    unit_system: str
    servers: list

    def save(self):
        """Save settings to a configuration file."""
        serialise.dump(dataclasses.asdict(self), paths.SETTINGS, readable=True)
