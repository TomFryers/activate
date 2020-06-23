#!/usr/bin/env python3
import PyQt5
import ui
import load_gpx
import sys


def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    main_window = ui.MainWindow()
    main_window.show_on_map(load_gpx.load_gpx("test.gpx"))
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
