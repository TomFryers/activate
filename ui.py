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
        self.map.setView(default_map_location(route), 14)
        pyqtlet.L.polyline(route, {"smoothFactor": 0, "color": "#802090"}).addTo(
            self.map
        )

    def add_info(self, info):
        self.tableWidget.setRowCount(len(info))
        for i, (k, v) in enumerate(info.items()):
            self.tableWidget.setItem(i, 0, QtWidgets.QTableWidgetItem(k))
            self.tableWidget.setItem(i, 1, QtWidgets.QTableWidgetItem(v))
