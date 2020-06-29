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


class MinMax:
    def __init__(self):
        self.minimum = None
        self.maximum = None

    def update(self, value):
        if self.minimum is None:
            self.minimum = value
            self.maximum = value

        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

    @property
    def range(self):
        if self.minimum is None:
            return None
        return self.maximum - self.minimum

    @property
    def ratio(self):
        if self.minimum is None:
            return None
        return self.maximum / self.minimum


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

        self.charts = {}
        # Series is never accessed but it prevents the area charts
        # from having their line series garbage collected
        self.series = {}
        self.add_chart("ele", self.graphicsView, True)

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

    def add_chart(self, name, widget, area=False):
        chart = QtChart.QChart()
        chart.legend().hide()
        series = QtChart.QLineSeries()
        if area:
            area = QtChart.QAreaSeries()
            area.setUpperSeries(series)
            self.series[name] = series
            chart.addSeries(area)
        else:
            chart.addSeries(series)
        chart.createDefaultAxes()
        widget.setChart(chart)
        self.charts[name] = widget

    def update_chart(self, name, data):
        chart = self.charts[name].chart()
        series = chart.series()[0]
        if isinstance(series, QtChart.QAreaSeries):
            series = series.upperSeries()
        series.clear()
        x_range = MinMax()
        y_range = MinMax()
        for x, y in data:
            x_range.update(x)
            y_range.update(y)
            series.append(x, y)

        if x_range.minimum != 0 and x_range.ratio > 3:
            x_range.minimum = 0
        if y_range.minimum != 0 and y_range.ratio > 3:
            y_range.minimum = 0

        for i, axis in enumerate(
            (PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.Vertical)
        ):
            axis = chart.axes(axis)[0]
            if i == 0:
                axis.setRange(x_range.minimum, x_range.maximum)
            else:
                axis.setRange(y_range.minimum, y_range.maximum)
            axis.setTickCount((12, 4)[i])
            axis.applyNiceNumbers()
            interval = (axis.max() - axis.min()) / (axis.tickCount() - 1)
            if int(interval) == interval:
                axis.setLabelFormat("%i")
            else:
                axis.setLabelFormat(f"%.{max(0, -math.floor(math.log10(interval)))}f")

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
            self.update_chart(
                "ele",
                list(
                    zip(
                        [x / 1000 for x in activity.track.fields["dist"]],
                        activity.track.fields["ele"],
                    )
                ),
            )
