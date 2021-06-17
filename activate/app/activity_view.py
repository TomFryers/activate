"""Display an individual activity's data."""
import markdown
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal

from activate import activity_types, times
from activate.app import charts, photos
from activate.app.ui.activity_view import Ui_activity_view


class ActivityView(QtWidgets.QWidget, Ui_activity_view):
    """The statistics, graphs and map showing an activity."""

    closed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setup(self, unit_system, map_widget):
        self.unit_system = unit_system
        self.updated = set()
        self.map_widget = map_widget
        self.photo_list = photos.PhotoList(self)
        self.overview_tab_layout.addWidget(self.photo_list)

        for table in (self.split_table, self.info_table, self.curve_table):
            table.set_units(self.unit_system)
            table.setMouseTracking(True)
        self.info_table.cellEntered.connect(self.show_stat_point)
        self.split_table.cellEntered.connect(self.show_split)
        self.curve_table.cellEntered.connect(self.show_fastest)

        # Set up charts
        self.charts = charts.LineChartSet(self.unit_system, self.graphs_layout)
        self.charts.add("ele", area=True)
        self.charts.add("speed")
        self.charts.add("heartrate")
        self.charts.add("cadence")
        self.charts.add("power")
        for chart in self.charts.charts.values():
            chart.widget.mouse_moved.connect(self.show_marker)
        self.zones_chart = charts.Histogram([0], self.zones_graph, self.unit_system)
        self.curve_chart = charts.LineChart(
            self.curve_graph,
            self.unit_system,
            area=True,
            vertical_ticks=12,
            horizontal_log=True,
        )

    def update_splits(self, data):
        """Update the activity splits page."""
        self.split_table.update_data(data)

    def switch_to_summary(self):
        """Update labels, map and data box."""
        self.activity_name_label.setText(self.activity.name)
        self.flags_label.setText(" | ".join(self.activity.active_flags))
        self.description_label.setText(markdown.markdown(self.activity.description))
        self.date_time_label.setText(times.nice(self.activity.start_time))
        self.activity_type_label.setText(self.activity.sport)
        self.info_table.update_data(self.activity.stats)
        if self.activity.track.has_position_data:
            self.map_widget.setVisible(True)
            self.map_widget.show_route(self.activity.track.lat_lon_list)
            self.show_map()
        else:
            self.map_widget.setVisible(False)
        self.photo_list.show_activity_photos(self.activity)

    def switch_to_data(self):
        """Update charts."""
        if self.activity.track.has_altitude_data:
            self.charts.update_show("ele", [self.activity.track.graph("ele")])
        else:
            self.charts.hide("ele")
        self.charts.update_show("speed", [self.activity.track.graph("speed")])
        if "heartrate" in self.activity.track:
            self.charts.update_show(
                "heartrate", [self.activity.track.graph("heartrate")]
            )
        else:
            self.charts.hide("heartrate")
        if "cadence" in self.activity.track:
            self.charts.update_show("cadence", [self.activity.track.graph("cadence")])
        else:
            self.charts.hide("cadence")
        if "power" in self.activity.track:
            self.charts.update_show("power", [self.activity.track.graph("power")])
        else:
            self.charts.hide("power")

    def switch_to_splits(self):
        self.update_splits(
            self.activity.track.splits(
                splitlength=self.unit_system.units["distance"].size
            )
        )

    def switch_to_zones(self):
        zones = (
            activity_types.ZONES[self.activity.sport]
            if self.activity.sport in activity_types.ZONES
            else activity_types.ZONES[None]
        )
        zones = [self.unit_system.decode(x, "speed") for x in zones]
        self.zones_chart.set_zones(zones)
        self.zones_chart.update(self.activity.track.get_zone_durations(zones))

    @property
    def good_distances(self):
        return (
            activity_types.SPECIAL_DISTANCES[self.activity.sport]
            if self.activity.sport in activity_types.SPECIAL_DISTANCES
            else activity_types.SPECIAL_DISTANCES[None]
        )

    def switch_to_curve(self):
        table, graph, self.fastest_indices = self.activity.track.get_curve(
            self.good_distances
        )
        self.curve_chart.update([graph])
        self.curve_table.update_data(list(self.good_distances.values()), table)

    def update_page(self, page):
        """Switch to a new activity tab page."""
        if page in self.updated:
            return
        (
            self.switch_to_summary,
            self.switch_to_data,
            self.switch_to_splits,
            self.switch_to_zones,
            self.switch_to_curve,
        )[page]()
        self.updated.add(page)

    def force_update_page(self, page):
        """Update a page even if it already appears up to date."""
        if page in self.updated:
            self.updated.remove(page)
        self.update_page(page)

    def show_activity(self, new_activity):
        """Display a new activity."""
        self.activity = new_activity
        self.setWindowTitle(f"Analysing {self.activity.name}")
        if self.activity.track.manual:
            self.activity_tabs.setCurrentIndex(0)
        for page in range(1, 5):
            self.activity_tabs.setTabEnabled(page, not self.activity.track.manual)
        # Previously generated pages need refreshing
        self.updated = set()
        self.update_page(self.activity_tabs.currentIndex())

    def show_map(self):
        """
        Take back the map widget.

        This is necessary because the map widget must be shared between
        all layouts, and a widget cannot be in multiple places at once.
        Call this when the activity view becomes visible.
        """
        self.map_container.addWidget(self.map_widget)

    def show_marker(self, values):
        self.map_widget.remove_highlight()
        distance = values.x()
        self.charts.show_line(distance)
        distance = self.unit_system.decode(distance, "distance")
        point = self.activity.track.lat_lng_from_distance(distance)
        self.map_widget.show_marker(point)

    def show_split(self, split, _):
        self.map_widget.remove_marker()
        self.map_widget.show_highlight(
            self.activity.track.part_lat_lon_list(
                self.unit_system.decode(split, "distance"),
                self.unit_system.decode(split + 1, "distance"),
            )
        )

    def show_fastest(self, row, _):
        self.curve_chart.set_vertical_line(
            self.unit_system.encode(list(self.good_distances)[row], "distance")
        )
        self.map_widget.remove_marker()
        section = self.fastest_indices[row]
        self.map_widget.show_highlight(
            self.activity.track.lat_lon_list[section[0] : section[1]]
        )

    def show_stat_point(self, stat, _):
        stat = self.info_table.get_row_text(stat)[0]
        self.map_widget.remove_highlight()
        try:
            stat = {"Max. Speed": "speed", "Highest Point": "ele"}[stat]
        except KeyError:
            self.map_widget.remove_marker()
            return
        point = self.activity.track.max_point(stat)
        self.map_widget.show_marker(self.activity.track.lat_lon_list[point])

    def closeEvent(self, *args, **kwargs):
        self.closed.emit()
        super().closeEvent(*args, **kwargs)
