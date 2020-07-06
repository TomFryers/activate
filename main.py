#!/usr/bin/env python3
import sys

import PyQt5

import load_activity
import ui

try:
    import cPickle as pickle
except ImportError:
    import pickle


def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    main_window = ui.MainWindow()
    try:
        with open("activitycache.pickle", "rb") as f:
            cache = pickle.load(f)
    except FileNotFoundError:
        cache = {}
    activities = load_activity.load_all("originals", cache=cache)

    main_window.add_tracks(activities)
    main_window.show()
    exit_code = app.exec_()
    cache = {}
    for track in activities:
        cache.update(track.cache())
    with open("activitycache.pickle", "wb") as f:
        pickle.dump(cache, f)
    for activity in activities:
        activity.save("activities")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
