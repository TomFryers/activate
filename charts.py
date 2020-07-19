import datetime
import itertools
import math

import PyQt5
from PyQt5 import QtChart
from PyQt5.QtCore import Qt

import number_formats
import units


def axis_number_format(axis):
    """Format axis labels with the correct number of decimal places."""
    interval = (axis.max() - axis.min()) / (axis.tickCount() - 1)
    if interval.is_integer():
        axis.setLabelFormat("%i")
    else:
        axis.setLabelFormat(f"%.{max(0, -math.floor(math.log10(interval)))}f")


def date_axis_format(difference: datetime.timedelta) -> str:
    """Get the formatting for a date axis based on its range."""
    if difference >= datetime.timedelta(days=365):
        return "MMM yyyy"
    if difference >= datetime.timedelta(days=100):
        return "MMMM"
    if difference >= datetime.timedelta(days=5):
        return "dd MMMM"
    if difference >= datetime.timedelta(days=3):
        return "hh:00 d MMM"
    if difference >= datetime.timedelta(days=1):
        return "hh:mm d MMM"
    if difference >= datetime.timedelta(hours=12):
        return "hh:mm"
    return "hh:mm:ss"


class MinMax:
    """Keeps track of the minimum and maximum of some data."""

    def __init__(self, *args):
        if args:
            try:
                self.minimum = min(min(a) for a in args if a)
                self.maximum = max(max(a) for a in args if a)
                return
            # No values given
            except ValueError:
                pass
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

    def __repr__(self):
        if self.minimum is None:
            return f"{self.__class__.__name__}()"
        else:
            return f"{self.__class__.__name__}(({self.minimum!r}, {self.maximum!r}))"


def data_to_points(data):
    """Convert a [series1, series2] of data to a list of QPointF."""
    return [PyQt5.QtCore.QPointF(*p) for p in zip(*data)]


series_gc_prevent = []


class Chart(QtChart.QChart):
    """A chart with sensible defaults and extra functionality."""

    def __init__(self, seriess, widget, unit_system, title=None):
        """Create a new chart."""
        self.unit_system = unit_system
        super().__init__()
        self.setAnimationOptions(self.SeriesAnimations)
        widget.setRenderHint(PyQt5.QtGui.QPainter.Antialiasing, True)
        self.legend().hide()
        for series in seriess:
            self.addSeries(series)
        self.createDefaultAxes()
        widget.setChart(self)
        if title is not None:
            self.setTitle(title)

    def set_axis_dimensions(self, x_axis_dimension, y_axis_dimension):
        self.axes(Qt.Horizontal)[0].setTitleText(
            self.unit_system.format_axis_label(x_axis_dimension)
        )
        self.axes(Qt.Vertical)[0].setTitleText(
            self.unit_system.format_axis_label(y_axis_dimension)
        )


class LineChart(Chart):
    def __init__(self, widget, unit_system, title=None, area=False, series_count=1):
        """Add a line chart to widget."""
        seriess = []
        for _ in range(series_count):
            series = QtChart.QLineSeries()
            if area:
                area = QtChart.QAreaSeries()
                area.setUpperSeries(series)
                # Save series so it doesn't get garbage collected
                series_gc_prevent.append(series)
                series = area
            seriess.append(series)
        super().__init__(seriess, widget, unit_system, title)

    def encode_data(self, data):
        """Convert data with a dimension to floats with correct units."""
        return [
            [self.unit_system.encode(x, unit) for x in series] for series, unit in data
        ]

    def update(self, data):
        """Change a line chart's data."""
        x_dimension = data[0][0][1]
        y_dimension = data[0][1][1]
        self.set_axis_dimensions(x_dimension, y_dimension)
        data = [self.encode_data(d) for d in data]
        # Convert to the correct units
        seriess = self.series()
        # Extract 'real' series from an area chart
        seriess = [
            s.upperSeries() if isinstance(s, QtChart.QAreaSeries) else s
            for s in seriess
        ]
        x_range = MinMax(*(d[0] for d in data))
        y_range = MinMax(*(d[1] for d in data))
        for data_part, series in itertools.zip_longest(data, seriess):
            if data_part is None:
                series.setVisible(False)
            else:
                series.setVisible(True)
                series.replace(data_to_points(data_part))

        # Snap axis minima to zero
        if x_range.minimum != 0 and x_range.ratio > 3:
            x_range.minimum = 0
        if y_range.minimum != 0 and y_range.ratio > 3:
            y_range.minimum = 0

        self.update_axis(Qt.Horizontal, 12, x_range.minimum, x_range.maximum)
        self.update_axis(Qt.Vertical, 4, y_range.minimum, y_range.maximum)

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
        super().__init__([series], widget, unit_system)
        # Replace QBarCategoryAxis with QCategoryAxis because the latter
        # allows putting values between categoreies instead of centring
        # them.
        cat_axis = self.axes(Qt.Horizontal)[0]
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
        self.addAxis(cat_axis, Qt.AlignBottom)
        series.attachAxis(cat_axis)
        self.set_axis_dimensions("speed", "Time (min)")

    def update(self, data):
        """Update the histogram data."""
        series = self.series()[0]
        bar_set = series.barSets()[0]
        for position, amount in enumerate(data.values()):
            bar_set.replace(position, units.MINUTE.encode(amount))

        # Format the vertical axis
        value_axis = self.axes(Qt.Vertical)[0]
        value_axis.setRange(0, units.MINUTE.encode(max(data.values())))
        value_axis.setTickCount(15)
        value_axis.applyNiceNumbers()
        axis_number_format(value_axis)


class DateTimeLineChart(LineChart):
    """A line chart with datetimes on the x axis."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.removeAxis(self.axes(Qt.Horizontal)[0])
        self.date_time_axis = QtChart.QDateTimeAxis()
        self.addAxis(self.date_time_axis, Qt.AlignBottom)
        for series in self.series():
            series.attachAxis(self.date_time_axis)

    def encode_data(self, data):
        x_data = [self.unit_system.encode(x, data[0][1]) * 1000 for x in data[0][0]]
        y_data = [self.unit_system.encode(x, data[1][1]) for x in data[1][0]]
        return (x_data, y_data)

    def update_axis(self, direction, ticks, minimum, maximum):
        if direction == Qt.Horizontal:
            minimum = datetime.datetime.fromtimestamp(minimum / 1000)
            maximum = datetime.datetime.fromtimestamp(maximum / 1000)
            extra = (maximum - minimum) * 0.01
            minimum -= extra
            maximum += extra
            self.date_time_axis.setFormat(date_axis_format(maximum - minimum))
        super().update_axis(direction, ticks, minimum, maximum)
