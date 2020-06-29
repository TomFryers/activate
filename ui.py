import math

import PyQt5
import pyqtlet
from PyQt5 import QtChart, QtWidgets, uic

import times


def default_map_location(route):
    """Calculate the mean position for centering the map."""
    return [
        sum(i[0] for i in route) / len(route),
        sum(i[1] for i in route) / len(route),
    ]


class MinMax:
    """Keeps track of the minimum and maximum of some data."""

    def __init__(self):
        self.minimum = None
        self.maximum = None

    def update(self, value):
        """Add a new value to the MinMax."""
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
    """A sortable, formatted number to place in a table."""

    def __init__(self, number, text):
        super().__init__(text)
        self.number = number

    def __lt__(self, other):
        return self.number < other.number


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        uic.loadUi("main.ui", self)

        # Set up map
        self.map_widget = pyqtlet.MapWidget()
        self.map = pyqtlet.L.map(self.map_widget, {"attributionControl": False})
        self.map_container.addWidget(self.map_widget)
        self.map.setView([51, -1], 14)
        pyqtlet.L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png").addTo(self.map)

        # Set activity list heading resize modes
        header = self.activity_list_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)

        # Set up charts
        self.charts = {}
        # self.series is never accessed but it prevents the area charts
        # from having their line series garbage collected
        self.series = {}
        self.add_chart("ele", self.altitude_graph, True)
        self.add_chart("speed", self.speed_graph, False)

    def show_on_map(self, route: list):
        """Display a list of points on the map."""
        self.map.setView(default_map_location(route))
        try:
            self.map.removeLayer(self.route_line)
        except AttributeError:
            pass
        self.route_line = pyqtlet.L.polyline(
            route, {"smoothFactor": 0, "color": "#802090"}
        )
        self.route_line.addTo(self.map)

    def add_info(self, info: dict):
        """
        Add data to the table widget on the right.

        This is used for distance, climb, duration etc.
        """
        self.info_table.setRowCount(len(info))
        for i, (k, v) in enumerate(info.items()):
            self.info_table.setItem(i, 0, QtWidgets.QTableWidgetItem(k))
            # Format as number
            if isinstance(v, tuple):
                widget = FormattableNumber(*v)
            # Format as string
            else:
                widget = QtWidgets.QTableWidgetItem(v)
            widget.setTextAlignment(
                PyQt5.QtCore.Qt.AlignRight | PyQt5.QtCore.Qt.AlignVCenter
            )
            self.info_table.setItem(i, 1, widget)

    def add_tracks(self, activities):
        """Make the activity list show this set of activities."""
        self.activities = activities
        self.activity_list_table.setRowCount(len(activities))
        for i, activity in enumerate(activities):
            activity_elements = activity.list_row
            for j in range(len(activity_elements)):
                content = activity_elements[j]
                # Format as number
                if isinstance(content, tuple):
                    widget = FormattableNumber(*content)
                    widget.setTextAlignment(
                        PyQt5.QtCore.Qt.AlignRight | PyQt5.QtCore.Qt.AlignVCenter
                    )
                # Format as string
                else:
                    widget = QtWidgets.QTableWidgetItem(content)
                # Link activity to the first column so we can find it
                # when clicking
                if j == 0:
                    activity.list_link = widget
                self.activity_list_table.setItem(i, j, widget)
        self.activity_list_table.resizeColumnsToContents()

    def add_chart(self, name, widget: QtChart.QChartView, area=False):
        """Add a chart to a QChartView."""
        chart = QtChart.QChart()
        chart.setAnimationOptions(chart.SeriesAnimations)
        chart.legend().hide()
        series = QtChart.QLineSeries()
        if area:
            area = QtChart.QAreaSeries()
            area.setUpperSeries(series)
            # Save series so it doesn't get garbage collected
            self.series[name] = series
            chart.addSeries(area)
        else:
            chart.addSeries(series)
        chart.createDefaultAxes()
        widget.setChart(chart)
        self.charts[name] = widget

    def update_chart(self, name, data):
        """Change a chart's data."""
        chart = self.charts[name].chart()
        series = chart.series()[0]
        # Extract 'real' series from an area chart
        if isinstance(series, QtChart.QAreaSeries):
            series = series.upperSeries()
        series.clear()
        x_range = MinMax()
        y_range = MinMax()
        for x, y in data:
            x_range.update(x)
            y_range.update(y)
            series.append(x, y)

        # Snap axis minima to zero
        if x_range.minimum != 0 and x_range.ratio > 3:
            x_range.minimum = 0
        if y_range.minimum != 0 and y_range.ratio > 3:
            y_range.minimum = 0

        for i, axis in enumerate(
            (PyQt5.QtCore.Qt.Horizontal, PyQt5.QtCore.Qt.Vertical)
        ):
            axis = chart.axes(axis)[0]
            # Set the axis ranges
            if i == 0:
                axis.setRange(x_range.minimum, x_range.maximum)
            else:
                axis.setRange(y_range.minimum, y_range.maximum)
            axis.setTickCount((12, 4)[i])
            axis.applyNiceNumbers()

            # Set the correct axis label formatting
            interval = (axis.max() - axis.min()) / (axis.tickCount() - 1)
            if int(interval) == interval:
                axis.setLabelFormat("%i")
            else:
                axis.setLabelFormat(f"%.{max(0, -math.floor(math.log10(interval)))}f")

    def update(self, selected):
        """Show a new activity on the right."""
        # Find the correct activity
        for activity in self.activities:
            if activity.list_link is self.activity_list_table.item(selected, 0):
                break
        else:
            raise ValueError("Invalid selection made")

        # Update labels, map and data box
        self.activity_name_label.setText(activity.name)
        self.date_time_label.setText(times.nice(activity.start_time))
        self.add_info(activity.stats)
        self.show_on_map(activity.track.lat_lon_list)

        # Update charts
        if activity.track.has_altitude_data:
            self.update_chart(
                "ele",
                list(
                    zip(
                        [x / 1000 for x in activity.track["dist"]],
                        activity.track["ele"],
                    )
                ),
            )
        self.update_chart(
            "speed",
            list(
                zip(
                    [x / 1000 for x in activity.track["dist"]],
                    [x * 3.6 for x in activity.track["speed"]],
                )
            ),
        )
