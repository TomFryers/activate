"""Define some standard paths for storing data."""
import pathlib

from PyQt5.QtCore import QStandardPaths

DATA = f"{QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)}/activate/"
ACTIVITIES = DATA + "activities/"
TRACKS = DATA + "originals/"
SAVE = DATA + "activity_list.pickle"
SETTINGS = (
    QStandardPaths.writableLocation(QStandardPaths.ConfigLocation) + "/activate.pickle"
)
print(SETTINGS)


def ensure_exists(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def ensure_all_present():
    for path in (ACTIVITIES, TRACKS):
        ensure_exists(path)