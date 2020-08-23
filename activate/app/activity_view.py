import markdown

from PyQt5 import QtWidgets
from activate.app import charts, maps, photos
from activate.app.ui.activity_view import Ui_activity_view
from activate.core import activity_types, times


class ActivityView(QtWidgets.QWidget, Ui_activity_view):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setup(self, unit_system, map_widget):
        self.unit_system = unit_system
        self.updated = set()

        self.map_widget = map_widget

        self.photo_list = photos.PhotoList(self)
        self.overview_tab_layout.addWidget(self.photo_list, 1, 1)

        for table in (
            self.split_table,
            self.info_table,
            self.curve_table,
        ):
            table.set_units(self.unit_system)
        # Set up charts
        self.charts = charts.LineChartSet(self.unit_system, self.graphs_layout)
        self.charts.add("ele", area=True)
        self.charts.add("speed")
        self.charts.add("heartrate")
        self.charts.add("cadence")
        self.charts.add("power")

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
            self.map_widget.show(self.activity.track.lat_lon_list)
            self.map_container.addWidget(self.map_widget)
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

    def switch_to_curve(self):
        good_distances = (
            activity_types.SPECIAL_DISTANCES[self.activity.sport]
            if self.activity.sport in activity_types.SPECIAL_DISTANCES
            else activity_types.SPECIAL_DISTANCES[None]
        )
        table, graph = self.activity.track.get_curve(good_distances)
        self.curve_chart.update([graph])
        self.curve_table.update_data(list(good_distances.values()), table)

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
        if page in self.updated:
            self.updated.remove(page)
        self.update_page(page)

    def show_activity(self, new_activity):
        self.activity = new_activity
        if self.activity.track.manual:
            self.activity_tabs.setCurrentIndex(0)
        for page in range(1, 5):
            self.activity_tabs.setTabEnabled(page, not self.activity.track.manual)
        # Previously generated pages need refreshing
        self.updated = set()
        self.update_page(self.activity_tabs.currentIndex())

    def show_map(self):
        self.map_container.addWidget(self.map_widget)
