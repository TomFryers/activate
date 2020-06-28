import math

import PyQt5
import pyqtlet
from PyQt5 import QtChart, QtWidgets, uic

import times


def default_map_location(route):
    return [
        sum(i[0] for i in route) / len(route),
        sum(i[1] for i in route) / len(route),
    ]


class FormattableNumber(QtWidgets.QTableWidgetItem):
    def __init__(self, number, text):
        super().__init__(text)
        self.number = number

    def __lt__(self, other):
        return self.number < other.number


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
            if isinstance(v, tuple):
                widget = FormattableNumber(*v)
            else:
                widget = QtWidgets.QTableWidgetItem(v)
            widget.setTextAlignment(0x2 | 0x80)
            self.tableWidget.setItem(i, 1, widget)

    def add_tracks(self, activities):
        self.activities = activities
        self.tableWidget_2.setRowCount(len(activities))
        for i, activity in enumerate(activities):
            activity_elements = activity.list_row
            for j in range(len(activity_elements)):
                content = activity_elements[j]
                if isinstance(content, tuple):
                    widget = FormattableNumber(*content)
                    widget.setTextAlignment(0x2 | 0x80)
                else:
                    widget = QtWidgets.QTableWidgetItem(content)
                if j == 0:
                    activity.list_link = widget
                self.tableWidget_2.setItem(i, j, widget)
        self.tableWidget_2.resizeColumnsToContents()

    def update(self, selected):
        for activity in self.activities:
            if activity.list_link is self.tableWidget_2.item(selected, 0):
                break
        else:
            raise ValueError("Invalid selection made")

        self.label_2.setText(activity.name)
        self.label_3.setText(times.nice(activity.start_time))
        self.show_on_map(activity.track.lat_lon_list)
        self.add_info(activity.stats)

        # Charts
        if activity.track.has_altitude_data:
            self.altchart = QtChart.QChart()
            self.altchart.legend().hide()
            self.altseries = QtChart.QLineSeries()
            for distance, elevation in zip(
                activity.track.fields["dist"], activity.track.fields["ele"]
            ):
                self.altseries.append(distance / 1000, elevation)

            area = QtChart.QAreaSeries()
            area.setUpperSeries(self.altseries)
            self.altchart.addSeries(area)
            self.altchart.createDefaultAxes()
            for i, axis in enumerate(
                (
                    self.altchart.axes(PyQt5.QtCore.Qt.Horizontal)[0],
                    self.altchart.axes(PyQt5.QtCore.Qt.Vertical)[0],
                )
            ):
                axis.setTickCount((12, 5)[i])
                axis.applyNiceNumbers()
                interval = (axis.max() - axis.min()) / (axis.tickCount() - 1)
                if int(interval) == interval:
                    axis.setLabelFormat("%i")
                else:
                    axis.setLabelFormat(
                        f"%.{max(0, -math.floor(math.log10(interval)))}f"
                    )
            self.graphicsView.setChart(self.altchart)
