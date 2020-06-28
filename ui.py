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

    def add_tracks(self, activities):
        self.activities = activities
        self.tableWidget_2.setRowCount(len(activities))
        for i, activity in enumerate(activities):
            activity_elements = activity.list_row
            for j in range(len(activity_elements)):
                widget = QtWidgets.QTableWidgetItem(activity_elements[j])
                if j == 0:
                    activity.list_link = widget
                self.tableWidget_2.setItem(i, j, widget)

    def update(self, selected):
        for activity in self.activities:
            if activity.list_link is self.tableWidget_2.item(selected.row(), 0):
                break
        else:
            raise ValueError("Invalid selection made")

        self.label_2.setText(activity.name)
        self.show_on_map(activity.track.lat_lon_list)
        self.add_info(activity.stats)
