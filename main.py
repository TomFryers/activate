#!/usr/bin/env python3
import sys

import PyQt5

import load_gpx
import times
import ui


def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    main_window = ui.MainWindow()
    tracks = load_gpx.load_all("tracks")
    main_window.add_tracks(tracks)
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
