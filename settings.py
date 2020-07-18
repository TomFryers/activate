import dataclasses
import pickle

import units

SETTINGS_PATH = "settings.pickle"


def load_settings():
    """Load settings from a configuration file."""
    try:
        with open(SETTINGS_PATH, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return Settings(unit_system=units.DEFAULT)


@dataclasses.dataclass
class Settings:
    """A settings configuration"""

    unit_system: str

    def save(self):
        """Save settings to a configuration file."""
        with open(SETTINGS_PATH, "wb") as f:
            pickle.dump(self, f)
