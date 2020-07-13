#!/usr/bin/env python3
import sys

import PyQt5

import activity_list
import ui


def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    activities = activity_list.from_disk()
    main_window = ui.MainWindow(activities)

    main_window.show()
    exit_code = app.exec_()
    activities.save()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
