#!/usr/bin/env python3
import sys

import PyQt5

import load_gpx
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
    activities = load_gpx.load_all("tracks", cache=cache)
    cache = {}
    for track in activities:
        cache.update(track.cache())
    with open("activitycache.pickle", "wb") as f:
        pickle.dump(cache, f)

    main_window.add_tracks(activities)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
