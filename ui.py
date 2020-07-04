import math

import PyQt5
import pyqtlet
from PyQt5 import QtChart, QtWidgets, uic

import load_activity
import number_formats
import settings
import times
import units


def default_map_location(route):
    """Calculate the mean position for centering the map."""
    return [
        (min(p[component] for p in route) + max(p[component] for p in route)) / 2
        for component in range(2)
    ]


class MinMax:
    """Keeps track of the minimum and maximum of some data."""

    def __init__(self, *args):
        if args:
            self.minimum = min(min(a) for a in args)
            self.maximum = max(max(a) for a in args)
        else:
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


def create_table_item(item, align=None) -> QtWidgets.QTableWidgetItem:
    """
    Create a table item that can be a FormattableNumber.

    If item is a tuple, will return a table item that looks like item[1]
    but sorts with item[0]. Otherwise just returns a normal table item.
    """
    if isinstance(item, tuple):
        widget = FormattableNumber(*item)
    # Format as string
    else:
        widget = QtWidgets.QTableWidgetItem(item)
        widget.setTextAlignment(
            PyQt5.QtCore.Qt.AlignRight | PyQt5.QtCore.Qt.AlignVCenter
        )
    if align is not None:
        widget.setTextAlignment(align)
    return widget


def good_minus(string):
    """Replace hyphen-minuses with real minus signs."""
    return string.replace("-", "\u2212")


class FormattableNumber(QtWidgets.QTableWidgetItem):
    """A sortable, formatted number to place in a table."""

    def __init__(self, number, text):
        super().__init__(good_minus(text))
        self.number = number

    def __lt__(self, other):
        return self.number < other.number


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("settings.ui", self)

    def load_from_settings(self, current_settings: settings.Settings):
        """Load a settings object to the UI widgets."""
        self.unit_system.setCurrentText(current_settings.unit_system)

    def get_settings(self) -> settings.Settings:
        """Get a settings object from the UIT widgets."""
        return settings.Settings(unit_system=self.unit_system.currentText())

    def exec(self, current_settings, page):
        self.settings_tabs.setCurrentIndex(("Units",).index(page))
        result = super().exec()
        if not result:
            return current_settings
        settings = self.get_settings()
        settings.save()
        return settings


def resize_to_contents(header):
    """
    Set a header to auto-resize its items.

    This also stops the user resizing them, which is good because usually
    resizing these things is not particularly useful.
    """
    header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        uic.loadUi("main.ui", self)
        self.updated = set()

        # Set up map
        self.map_widget = pyqtlet.MapWidget()
        self.map_widget.setContextMenuPolicy(PyQt5.QtCore.Qt.NoContextMenu)
        self.map = pyqtlet.L.map(self.map_widget, {"attributionControl": False})
        self.map_container.addWidget(self.map_widget)
        self.map.setView([51, -1], 14)
        pyqtlet.L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png").addTo(self.map)

        # Set activity list heading resize modes
        header = self.activity_list_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)

        # Disable resizing in activity list
        resize_to_contents(self.activity_list_table.verticalHeader())
        resize_to_contents(self.split_table.horizontalHeader())

        # Set up charts
        self.charts = {}
        # self.series is never accessed but it prevents the area charts
        # from having their line series garbage collected
        self.series = {}
        self.add_chart("ele", self.altitude_graph, True)
        self.add_chart("speed", self.speed_graph, False)

        self.action_import.setIcon(PyQt5.QtGui.QIcon.fromTheme("document-open"))
        self.action_quit.setIcon(PyQt5.QtGui.QIcon.fromTheme("application-exit"))

        self.settings = settings.load_settings()

    def edit_unit_settings(self):
        settings_window = SettingsDialog()
        self.settings = settings_window.exec(self.settings, "Units")

    def show_on_map(self, route: list):
        """Display a list of points on the map."""
        self.map.setView(default_map_location(route))
        try:
            self.map.removeLayer(self.route_line)
            self.map.removeLayer(self.start_icon)
            self.map.removeLayer(self.finish_icon)
        except AttributeError:
            pass
        self.route_line = pyqtlet.L.polyline(
            route, {"smoothFactor": 0, "color": "#802090"}
        )
        self.start_icon = pyqtlet.L.circleMarker(
            route[0], {"radius": 8, "color": "#10b020"}
        )
        self.finish_icon = pyqtlet.L.circleMarker(
            route[-1], {"radius": 8, "color": "#e00000"}
        )
        self.start_icon.addTo(self.map)
        self.finish_icon.addTo(self.map)
        self.route_line.addTo(self.map)

    def add_info(self, info: dict):
        """
        Add data to the table widget on the right.

        This is used for distance, climb, duration etc.
        """
        self.info_table.setRowCount(len(info))
        for i, (k, v) in enumerate(info.items()):
            self.info_table.setItem(i, 0, create_table_item(k))
            if isinstance(v, tuple):
                value, unit = self.unit_system.format(*v)
            else:
                value = v
                unit = None
            self.info_table.setItem(
                i,
                1,
                create_table_item(
                    (value, number_formats.info_format(value, k)),
                    align=PyQt5.QtCore.Qt.AlignRight | PyQt5.QtCore.Qt.AlignVCenter,
                ),
            ),
            self.info_table.setItem(
                i,
                2,
                create_table_item(
                    unit, align=PyQt5.QtCore.Qt.AlignLeft | PyQt5.QtCore.Qt.AlignVCenter
                ),
            )

    def add_tracks(self, activities):
        """Make the activity list show this set of activities."""
        self.activities = activities
        self.activity_list_table.setRowCount(len(activities))
        for i, activity in enumerate(activities):
            self.add_activity(i, activity)
        self.activity_list_table.resizeColumnsToContents()
        self.activity_list_table.sortItems(1, PyQt5.QtCore.Qt.DescendingOrder)

    def add_activity(self, position, activity):
        """Add an activity to the activity list."""
        activity_elements = activity.list_row
        for j, content in enumerate(activity_elements):
            needs_special_sorting = False
            # Format as number
            if isinstance(content, tuple):
                needs_special_sorting = True
                content = self.unit_system.encode(*content)
            text = number_formats.list_format(
                content, self.activity_list_table.horizontalHeaderItem(j).text()
            )
            if needs_special_sorting:
                widget = create_table_item((content, text))
            else:
                widget = create_table_item(text)
            # Link activity to the first column so we can find it
            # when clicking
            if j == 0:
                activity.list_link = widget
            self.activity_list_table.setItem(position, j, widget)

    def add_chart(self, name, widget: QtChart.QChartView, area=False):
        """Add a chart to a QChartView."""
        chart = QtChart.QChart()
        chart.setAnimationOptions(chart.SeriesAnimations)
        chart.setTitle({"ele": "Altitude", "speed": "Speed"}[name])
        widget.setRenderHint(PyQt5.QtGui.QPainter.Antialiasing, True)
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
        # Convert to the correct units
        data = [
            [self.unit_system.encode(x, unit) for x in series] for series, unit in data
        ]
        chart = self.charts[name].chart()
        series = chart.series()[0]
        # Extract 'real' series from an area chart
        if isinstance(series, QtChart.QAreaSeries):
            series = series.upperSeries()
        x_range = MinMax(data[0])
        y_range = MinMax(data[1])
        series.replace([PyQt5.QtCore.QPointF(*p) for p in zip(*data)])

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

    def update_splits(self, data):
        """Update the activity splits page."""
        self.split_table.setRowCount(len(data))
        for y, row in enumerate(data):
            for x, item in enumerate([(y + 1, None)] + row):
                if isinstance(item, tuple):
                    item = self.unit_system.encode(*item)
                self.split_table.setItem(
                    y,
                    x,
                    create_table_item(
                        (
                            item,
                            number_formats.split_format(
                                item, self.split_table.horizontalHeaderItem(x).text()
                            ),
                        ),
                        PyQt5.QtCore.Qt.AlignRight | PyQt5.QtCore.Qt.AlignVCenter,
                    ),
                )

    def update_page(self, page):
        """Switch to a new activity tab page."""
        if page in self.updated:
            return
        if page == 0:
            # Update labels, map and data box
            self.activity_name_label.setText(self.activity.name)
            self.date_time_label.setText(times.nice(self.activity.start_time))
            self.add_info(self.activity.stats)
            self.show_on_map(self.activity.track.lat_lon_list)
        elif page == 1:
            # Update charts
            if self.activity.track.has_altitude_data:
                self.update_chart("ele", self.activity.track.alt_graph)
            self.update_chart("speed", self.activity.track.speed_graph)
        elif page == 2:
            self.update_splits(self.activity.track.splits)
        self.updated.add(page)

    def update_activity(self, selected):
        """Show a new activity on the right."""
        # Find the correct activity
        for activity in self.activities:
            if activity.list_link is self.activity_list_table.item(selected, 0):
                break
        else:
            raise ValueError("Invalid selection made")
        self.activity = activity

        # Previously generated pages need refreshing
        self.updated = set()
        self.update_page(self.activity_tabs.currentIndex())

    def import_activity(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import an activity", "", "Activity Files (*.gpx *.fit)"
        )[0]
        if not filename:
            return
        activity = load_activity.import_and_load(filename)
        self.activity_list_table.setSortingEnabled(False)
        self.activity_list_table.insertRow(0)
        self.add_activity(0, activity)
        self.activity_list_table.setSortingEnabled(True)
        self.activities.append(activity)
        self.activity_list_table.setCurrentItem(activity.list_link)

    @property
    def unit_system(self):
        return units.UNIT_SYSTEMS[self.settings.unit_system]
