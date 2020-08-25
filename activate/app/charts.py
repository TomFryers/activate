"""Custom QCharts."""
import datetime
import itertools
import math

import PyQt5
from PyQt5 import QtChart
from PyQt5.QtCore import Qt

from activate.core import number_formats, units


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
        return f"{self.__class__.__name__}(({self.minimum!r}, {self.maximum!r}))"


def data_to_points(data):
    """Convert a [series1, series2] of data to a list of QPointF."""
    return [PyQt5.QtCore.QPointF(*p) for p in zip(*data)]


series_gc_prevent = []


def create_axis(log=False):
    if log:
        axis = QtChart.QLogValueAxis()
        axis.setMinorTickCount(-1)
        axis.setLabelFormat("%g")
        return axis
    return QtChart.QValueAxis()


class Chart(QtChart.QChart):
    """A chart with sensible defaults and extra functionality."""

    def __init__(
        self,
        seriess,
        widget,
        unit_system,
        title=None,
        horizontal_ticks=12,
        vertical_ticks=5,
        horizontal_log=False,
        vertical_log=False,
    ):
        """Create a new chart."""
        self.unit_system = unit_system
        self.horizontal_ticks = horizontal_ticks
        self.vertical_ticks = vertical_ticks
        self.horizontal_log = horizontal_log
        self.vertical_log = vertical_log
        super().__init__()
        self.setAnimationOptions(self.SeriesAnimations)
        widget.setRenderHint(PyQt5.QtGui.QPainter.Antialiasing, True)
        self.legend().hide()

        x_axis = create_axis(horizontal_log)
        y_axis = create_axis(vertical_log)
        self.addAxis(x_axis, Qt.AlignBottom)
        self.addAxis(y_axis, Qt.AlignLeft)
        for series in seriess:
            self.addSeries(series)
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)
        widget.setChart(self)
        if title is not None:
            self.setTitle(title)

    def set_axis_dimensions(self, x_axis_dimension, y_axis_dimension):
        self.axes(Qt.Horizontal)[0].setTitleText(
            self.unit_system.format_name_unit(x_axis_dimension)
        )
        self.axes(Qt.Vertical)[0].setTitleText(
            self.unit_system.format_name_unit(y_axis_dimension)
        )

    def update_axis(self, direction, ticks, minimum, maximum):
        """Change an axis range to fit minimum and maximum."""
        axis = self.axes(direction)[0]
        if isinstance(axis, QtChart.QValueAxis):
            fake_axis = QtChart.QValueAxis()
            fake_axis.setRange(minimum, maximum)
            fake_axis.setTickCount(ticks)
            fake_axis.applyNiceNumbers()
            axis.setRange(fake_axis.min(), fake_axis.max())
            axis.setTickCount(fake_axis.tickCount())
            axis_number_format(axis)
        elif isinstance(axis, QtChart.QLogValueAxis):
            # Minimum must be decreased slightly to add the necessary extra tick
            axis.setRange(minimum / 1.00001, maximum)
        # For date axes in subclass
        else:
            axis.setRange(minimum, maximum)
            axis.setTickCount(ticks)


class LineChart(Chart):
    """A chart with 1+ QLineSeries on it."""

    def __init__(
        self,
        widget,
        unit_system,
        title=None,
        area=False,
        series_count=1,
        horizontal_ticks=12,
        vertical_ticks=5,
        horizontal_log=False,
        vertical_log=False,
    ):
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
        super().__init__(
            seriess,
            widget,
            unit_system,
            title,
            horizontal_ticks,
            vertical_ticks,
            horizontal_log,
            vertical_log,
        )

    def encode_data(self, data):
        """Convert data with a dimension to floats with correct units."""
        # Convert units
        data = zip(
            *(
                [
                    None if x is None else self.unit_system.encode(x, unit)
                    for x in series
                ]
                for series, unit in data
            )
        )
        # Get rid of Nones
        return list(zip(*(p for p in data if None not in p)))

    @property
    def data_series(self):
        return [
            s.upperSeries() if isinstance(s, QtChart.QAreaSeries) else s
            for s in self.series()
        ]

    def clear(self):
        for series in self.data_series:
            series.setVisible(False)

    def update(self, data):
        """Change a line chart's data."""
        x_dimension = data[0][0][1]
        y_dimension = data[0][1][1]
        self.set_axis_dimensions(x_dimension, y_dimension)
        # Convert to the correct units
        data = [self.encode_data(d) for d in data]
        # Extract 'real' series from an area chart
        x_range = MinMax(*(d[0] for d in data))
        y_range = MinMax(*(d[1] for d in data))
        for data_part, series in itertools.zip_longest(data, self.data_series):
            if data_part is None:
                series.setVisible(False)
            else:
                series.setVisible(True)
                series.replace(data_to_points(data_part))

        # Snap axis minima to zero
        if not self.horizontal_log and x_range.minimum != 0 and x_range.ratio > 3:
            x_range.minimum = 0
        if not self.vertical_log and y_range.minimum != 0 and y_range.ratio > 3:
            y_range.minimum = 0

        self.update_axis(
            Qt.Horizontal, self.horizontal_ticks, x_range.minimum, x_range.maximum
        )
        self.update_axis(
            Qt.Vertical, self.vertical_ticks, y_range.minimum, y_range.maximum
        )


class LineChartSet:
    """A set of line charts that can be hidden and shown."""

    def __init__(self, unit_system, container):
        self.unit_system = unit_system
        self.container = container
        self.charts = {}
        self.chart_views = {}

    def add(self, name, area=False):
        self.chart_views[name] = QtChart.QChartView()
        self.charts[name] = LineChart(
            self.chart_views[name], self.unit_system, area=area
        )
        self.container.addWidget(self.chart_views[name], 1)

    def __getitem__(self, name):
        return self.charts[name]

    def show(self, name):
        self.chart_views[name].setVisible(True)

    def hide(self, name):
        self.chart_views[name].setVisible(False)

    def update_show(self, name, data):
        self[name].update(data)
        self.show(name)

    def __repr__(self):
        return f"<LineChartSet charts={self.charts!r}>"


class Histogram(Chart):
    def __init__(self, zones, widget, unit_system):
        """Create a histogram."""
        series = QtChart.QBarSeries()
        bar_set = QtChart.QBarSet("", series)
        series.append(bar_set)
        series.setBarWidth(1)
        super().__init__([series], widget, unit_system)
        self.set_zones(zones)

    def set_zones(self, zones):
        # Use QBarCategoryAxis instead of QCategoryAxis because the
        # latter allows putting values between categoreies instead of
        # centring them.
        cat_axis = self.axes(Qt.Horizontal)[0]
        self.removeAxis(cat_axis)
        cat_axis = QtChart.QCategoryAxis(self)
        cat_axis.setLabelsPosition(QtChart.QCategoryAxis.AxisLabelsPositionOnValue)
        # Hide the start value because zones[0] does its job
        cat_axis.setStartValue(float("-inf"))

        # Add initial label, handling negative infinity.
        if zones[0] == float("-inf"):
            cat_axis.append("\u2212\u221e", -0.5)
        else:
            zone_num = self.unit_system.encode(zones[0], "speed")
            cat_axis.append(number_formats.maybe_as_int(zone_num), -0.5)

        # Add axis labels
        for position, zone in enumerate(zones[1:-1]):
            zone_num = self.unit_system.encode(zone, "speed")
            cat_axis.append(number_formats.maybe_as_int(zone_num), position + 0.5)

        # Add final label. This should usually be infinity.
        if zones[-1] == float("inf"):
            cat_axis.append("\u221e", len(zones) - 1.5)
        else:
            zone_num = self.unit_system.encode(zones[-1], "speed")
            cat_axis.append(number_formats.maybe_as_int(zone_num), len(zones) - 1.5)

        cat_axis.setRange(-0.5, len(zones) - 1.5)

        # One less bar than there are zones borders
        series = self.series()[0]
        bar_set = series.barSets()[0]
        if bar_set.count() > len(zones) - 1:
            bar_set.remove(0, bar_set.count() - len(zones) + 1)
        elif bar_set.count() < len(zones) - 1:
            for _ in range(len(zones) - 1 - bar_set.count()):
                bar_set.append(0)
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
        self.update_axis(Qt.Vertical, 15, 0, units.MINUTE.encode(max(data.values())))


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
        """
        Convert the data provided to a more usable format.

        Input format: ((x_values, "time"), (y_values, y_format))
        Output format: (x_values, y_values)
        The output values are in the correct units for display on the
        chart.
        """
        x_data = [self.unit_system.encode(x, data[0][1]) * 1000 for x in data[0][0]]
        y_data = [self.unit_system.encode(x, data[1][1]) for x in data[1][0]]
        return (x_data, y_data)

    def update_axis(self, direction, ticks, minimum, maximum):
        """Resize the chart axes."""
        if direction == Qt.Horizontal:
            minimum = datetime.datetime.fromtimestamp(minimum / 1000)
            maximum = datetime.datetime.fromtimestamp(maximum / 1000)
            extra = (maximum - minimum) * 0.01
            minimum -= extra
            maximum += extra
            self.date_time_axis.setFormat(date_axis_format(maximum - minimum))
        super().update_axis(direction, ticks, minimum, maximum)
