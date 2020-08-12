"""Contains a class holding current user settings."""
import dataclasses

from activate.app import paths
from activate.core import serialise, units


def load_settings():
    """Load settings from a configuration file."""
    try:
        return Settings(**serialise.load_file(paths.SETTINGS))
    except FileNotFoundError:
        return Settings(unit_system=units.DEFAULT)


@dataclasses.dataclass
class Settings:
    """A settings configuration"""

    unit_system: str

    def save(self):
        """Save settings to a configuration file."""
        dict_version = dataclasses.asdict(self)
        serialise.dump_file(dict_version, paths.SETTINGS, readable=True)
