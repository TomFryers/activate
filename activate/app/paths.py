"""Define some standard paths for storing data."""
import pathlib

from PyQt5.QtCore import QStandardPaths

DATA = f"{QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)}/activate/"
ACTIVITIES = DATA + "activities/"
TRACKS = DATA + "originals/"
PHOTOS = DATA + "photos/"
SAVE = DATA + "activity_list.pickle"
SETTINGS = (
    QStandardPaths.writableLocation(QStandardPaths.ConfigLocation) + "/activate.pickle"
)
HOME = QStandardPaths.writableLocation(QStandardPaths.HomeLocation) + "/"


def ensure_exists(path):
    """Create a directory if it doesn't already exist."""
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def ensure_all_present():
    """Create all the required directories."""
    for path in (ACTIVITIES, TRACKS, PHOTOS):
        ensure_exists(path)
