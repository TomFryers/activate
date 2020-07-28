"""Contains a class holding current user settings."""
import dataclasses
import pickle

from activate.app import paths
from activate.core import units


def load_settings():
    """Load settings from a configuration file."""
    try:
        with open(paths.SETTINGS, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return Settings(unit_system=units.DEFAULT)


@dataclasses.dataclass
class Settings:
    """A settings configuration"""

    unit_system: str

    def save(self):
        """Save settings to a configuration file."""
        with open(paths.SETTINGS, "wb") as f:
            pickle.dump(self, f)
