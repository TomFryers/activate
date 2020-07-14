import datetime
import math

import PyQt5
from PyQt5 import QtChart

import number_formats
import units


def axis_number_format(axis):
    """Format axis labels with the correct number of decimal places."""
    interval = (axis.max() - axis.min()) / (axis.tickCount() - 1)
    if interval.is_integer():
        axis.setLabelFormat("%i")
    else:
        axis.setLabelFormat(f"%.{max(0, -math.floor(math.log10(interval)))}f")


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


def data_to_points(data):
    """Convert a [series1, series2] of data to a list of QPointF."""
    return [PyQt5.QtCore.QPointF(*p) for p in zip(*data)]


series_gc_prevent = []


class Chart(QtChart.QChart):
    """A chart with sensible defaults and extra functionality."""

    def __init__(self, series, widget, unit_system, title=None):
        """Create a new chart."""
        self.unit_system = unit_system
        super().__init__()
        self.setAnimationOptions(self.SeriesAnimations)
        widget.setRenderHint(PyQt5.QtGui.QPainter.Antialiasing, True)
        self.legend().hide()
        self.addSeries(series)
        self.createDefaultAxes()
        widget.setChart(self)
        if title is not None:
            self.setTitle(title)


class LineChart(Chart):
    def __init__(self, widget, unit_system, title=None, area=False):
        """Add a line chart to widget."""
        series = QtChart.QLineSeries()
        if area:
            area = QtChart.QAreaSeries()
            area.setUpperSeries(series)
            # Save series so it doesn't get garbage collected
            series_gc_prevent.append(series)
            series = area
        super().__init__(series, widget, unit_system, title)

    def encode_data(self, data):
        return [
            [self.unit_system.encode(x, unit) for x in series] for series, unit in data
        ]

    def update(self, data):
        """Change a line chart's data."""
        data = self.encode_data(data)
        # Convert to the correct units
        series = self.series()[0]
        # Extract 'real' series from an area chart
        if isinstance(series, QtChart.QAreaSeries):
            series = series.upperSeries()
        x_range = MinMax(data[0])
        y_range = MinMax(data[1])
        series.replace(data_to_points(data))

        # Snap axis minima to zero
        if x_range.minimum != 0 and x_range.ratio > 3:
            x_range.minimum = 0
        if y_range.minimum != 0 and y_range.ratio > 3:
            y_range.minimum = 0

        self.update_axis(
            PyQt5.QtCore.Qt.Horizontal, 12, x_range.minimum, x_range.maximum
        )
        self.update_axis(PyQt5.QtCore.Qt.Vertical, 4, y_range.minimum, y_range.maximum)

    def update_axis(self, direction, ticks, minimum, maximum):
        axis = self.axes(direction)[0]
        axis.setRange(minimum, maximum)
        axis.setTickCount(ticks)
        try:
            axis.applyNiceNumbers()
            # Set the correct axis label formatting
            axis_number_format(axis)
        # For date axes in subclass
        except AttributeError:
            pass


class Histogram(Chart):
    def __init__(self, zones, widget, unit_system):
        """Create a histogram."""
        series = QtChart.QBarSeries()
        bar_set = QtChart.QBarSet("", series)
        # One less bar than there are zones
        for _ in zones[:-1]:
            bar_set.append(0)
        series.append(bar_set)
        series.setBarWidth(1)
        super().__init__(series, widget, unit_system)
        # Replace QBarCategoryAxis with QCategoryAxis because the latter
        # allows putting values between categoreies instead of centring
        # them.
        cat_axis = self.axes(PyQt5.QtCore.Qt.Horizontal)[0]
        self.removeAxis(cat_axis)
        cat_axis = QtChart.QCategoryAxis(self)

        # Hide the start value because zones[0] does its job
        cat_axis.setStartValue(float("-inf"))

        # Add initial label, handling negative infinity.
        if zones[0] == float("-inf"):
            cat_axis.append("\u2212\u221e", -0.5)
        else:
            cat_axis.append(number_formats.maybe_as_int(zones[0]), -0.5)

        # Add axis labels
        for position, zone in enumerate(zones[1:-1]):
            zone_num = self.unit_system.encode(zone, "speed")
            cat_axis.append(number_formats.maybe_as_int(zone_num), position + 0.5)

        # Add final label. This should usually be infinity.
        if zones[-1] == float("inf"):
            cat_axis.append("\u221e", len(zones) - 1.5)
        else:
            cat_axis.append(number_formats.maybe_as_int(zones[-1]), len(zones) - 1.5)

        cat_axis.setLabelsPosition(QtChart.QCategoryAxis.AxisLabelsPositionOnValue)
        self.addAxis(cat_axis, PyQt5.QtCore.Qt.AlignBottom)
        series.attachAxis(cat_axis)

    def update(self, data):
        """Update the histogram data."""
        series = self.series()[0]
        bar_set = series.barSets()[0]
        for position, amount in enumerate(data.values()):
            bar_set.replace(position, units.MINUTE.encode(amount))

        # Format the vertical axis
        value_axis = self.axes(PyQt5.QtCore.Qt.Vertical)[0]
        value_axis.setRange(0, units.MINUTE.encode(max(data.values())))
        value_axis.setTickCount(15)
        value_axis.applyNiceNumbers()
        axis_number_format(value_axis)


class DateTimeLineChart(LineChart):
    def __init__(self, *args):
        super().__init__(*args)
        self.removeAxis(self.axes(PyQt5.QtCore.Qt.Horizontal)[0])
        self.date_time_axis = QtChart.QDateTimeAxis()
        self.addAxis(self.date_time_axis, PyQt5.QtCore.Qt.AlignBottom)
        self.series()[0].attachAxis(self.date_time_axis)

    def encode_data(self, data):
        x_data = [self.unit_system.encode(x, data[0][1]) * 1000 for x in data[0][0]]
        y_data = [self.unit_system.encode(x, data[1][1]) for x in data[1][0]]
        return (x_data, y_data)

    def update_axis(self, direction, ticks, minimum, maximum):
        if direction == PyQt5.QtCore.Qt.Horizontal:
            minimum = datetime.datetime.fromtimestamp(minimum / 1000)
            maximum = datetime.datetime.fromtimestamp(maximum / 1000)
            extra = (maximum - minimum) * 0.01
            minimum -= extra
            maximum += extra
            x_range = maximum - minimum
            if x_range >= datetime.timedelta(days=365):
                self.date_time_axis.setFormat("MMM yyyy")
            elif x_range >= datetime.timedelta(days=100):
                self.date_time_axis.setFormat("MMMM")
            elif x_range >= datetime.timedelta(days=5):
                self.date_time_axis.setFormat("dd MMMM")
            elif x_range >= datetime.timedelta(days=3):
                self.date_time_axis.setFormat("hh:00 d MMM")
            elif x_range >= datetime.timedelta(days=1):
                self.date_time_axis.setFormat("hh:mm d MMM")
            elif x_range >= datetime.timedelta(hours=12):
                self.date_time_axis.setFormat("hh:mm")
            else:
                self.date_time_axis.setFormat("hh:mm:ss")

        super().update_axis(direction, ticks, minimum, maximum)
