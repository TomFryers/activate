#!/usr/bin/env python3
import sys

import PyQt5

import load_gpx
import times
import ui


def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    main_window = ui.MainWindow()
    gpx = load_gpx.load_gpx("test.gpx")
    main_window.show_on_map(gpx.lat_lon_list)
    main_window.add_info(
        {
            "Distance": str(round(gpx.length / 1000, 1)),
            "Ascent": str(round(gpx.ascent)),
            "Elapsed Time": times.to_string(gpx.elapsed_time),
        }
    )
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
