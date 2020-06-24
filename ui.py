import times

import pyqtlet
from PyQt5 import QtWidgets, uic


def default_map_location(route):
    return [
        sum(i[0] for i in route) / len(route),
        sum(i[1] for i in route) / len(route),
    ]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        uic.loadUi("main.ui", self)

        self.mapWidget = pyqtlet.MapWidget()
        self.map = pyqtlet.L.map(self.mapWidget, {"attributionControl": False})
        self.mapContainer.addWidget(self.mapWidget)
        self.map.setView([51, -1], 14)
        pyqtlet.L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png").addTo(self.map)

    def show_on_map(self, route):
        self.map.setView(default_map_location(route))
        try:

            self.map.removeLayer(self.route_line)
        except AttributeError:
            pass
        self.route_line = pyqtlet.L.polyline(
            route, {"smoothFactor": 0, "color": "#802090"}
        )
        self.route_line.addTo(self.map)

    def add_info(self, info):
        self.tableWidget.setRowCount(len(info))
        for i, (k, v) in enumerate(info.items()):
            self.tableWidget.setItem(i, 0, QtWidgets.QTableWidgetItem(k))
            self.tableWidget.setItem(i, 1, QtWidgets.QTableWidgetItem(v))

    def add_tracks(self, tracks):
        self.tracks = tracks
        self.tableWidget_2.setRowCount(len(tracks))
        for i, track in enumerate(tracks):
            self.tableWidget_2.setItem(
                i, 0, QtWidgets.QTableWidgetItem(track.name, type=1100 + i)
            )
            self.tableWidget_2.setItem(
                i, 1, QtWidgets.QTableWidgetItem(str(track.start_time))
            )
            self.tableWidget_2.setItem(
                i, 2, QtWidgets.QTableWidgetItem(str(round(track.length / 1000, 2)))
            )

    def update(self):
        selected = self.tableWidget_2.selectedItems()[0].type() - 1100
        track = self.tracks[selected]
        self.show_on_map(track.lat_lon_list)
        self.add_info(
            {
                "Distance": str(round(track.length / 1000, 2)),
                "Ascent": str(round(track.ascent)),
                "Elapsed Time": times.to_string(track.elapsed_time),
                "Average Speed": str(round(track.average_speed * 3.6, 2)),
            }
        )
