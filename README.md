# Activate

![Icon](activate/resources/icons/icon_cropped.png)

Activate is a free activity log and analysis tool.

The Python dependencies are:

- `PyQt5`
- `PyQtChart`
- `PyQtWebEngine`
- `pyqtlet`
- `Markdown`
- `fitparse`
- `requests`

`Flask` is also required for the server.

Run `make` to build the app.

Then, run `./app` to launch Activate, or `./setup.py install` to install it.

## Basic Usage

When you first open Activate, you will see a mostly empty screen with
your total distance, time, number of activities and climb (which are all
zero). To add your activities, go to File/Import or press Ctrl-I. Select
the activities you wish to import, and wait for the import to finish. If
you switch to the 'Activities' tab, you can see individual activities.
