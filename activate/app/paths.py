"""Define some standard paths for storing data."""
from pathlib import Path

from PyQt5.QtCore import QStandardPaths

# Locations for user data
DATA = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "activate"
)
ACTIVITIES = DATA / "activities"
TRACKS = DATA / "originals"
PHOTOS = DATA / "photos"

# Location for configuration files
SETTINGS = (
    Path(QStandardPaths.writableLocation(QStandardPaths.ConfigLocation))
    / "activate.json"
)

HOME = Path(QStandardPaths.writableLocation(QStandardPaths.HomeLocation))


def ensure_all_present():
    """Create all the required directories."""
    for path in (ACTIVITIES, TRACKS, PHOTOS):
        path.mkdir(parents=True, exist_ok=True)
