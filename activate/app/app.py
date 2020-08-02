#!/usr/bin/env python3
import datetime
import sys

import markdown
import PyQt5
import PyQt5.uic
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from activate.app import activity_list, charts, dialogs, maps, paths, settings
from activate.core import (
    activity_types,
    files,
    load_activity,
    number_formats,
    times,
    units,
)

NOW = datetime.datetime.now()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, activities, *args, **kwargs):
        self.activities = activities
        super(MainWindow, self).__init__(*args, **kwargs)

        PyQt5.uic.loadUi("resources/ui/main.ui", self)
        paths.ensure_all_present()
        self.updated = set()

        self.settings = settings.load_settings()

        self.activity_list_table.set_units(self.unit_system)
        self.split_table.set_units(self.unit_system)
        self.info_table.set_units(self.unit_system)
        self.curve_table.set_units(self.unit_system)

        self.update_activity_list()

        self.map_widget = maps.RouteMap(self.map_container)

        # Set up activity types list for the summary page
        self.do_not_recurse = True
        self.activity_types_list.addItems(["All"] + list(activity_types.TYPES))
        for i in range(len(["All"] + list(activity_types.TYPES))):
            self.activity_types_list.item(i).setCheckState(Qt.Checked)
        self.do_not_recurse = False

        # Set up charts
        self.charts = charts.LineChartSet(self.unit_system, self.graphs_layout)
        self.charts.add("ele", area=True)
        self.charts.add("speed")
        self.charts.add("heartrate")
        self.charts.add("cadence")
        self.charts.add("power")

        self.zones = list(range(0, 20)) + [float("inf")]
        self.zones = [self.unit_system.decode(x, "speed") for x in self.zones]
        self.zones_chart = charts.Histogram(
            self.zones, self.zones_graph, self.unit_system
        )

        self.curve_chart = charts.LineChart(
            self.curve_graph,
            self.unit_system,
            area=True,
            vertical_ticks=12,
            horizontal_log=True,
        )

        self.progression_chart = charts.DateTimeLineChart(
            self.progression_graph, self.unit_system, series_count=5, vertical_ticks=8
        )

        self.summary_period = "All Time"

        self.action_import.setIcon(PyQt5.QtGui.QIcon.fromTheme("document-open"))
        self.export_menu.setIcon(PyQt5.QtGui.QIcon.fromTheme("document-send"))
        self.action_quit.setIcon(PyQt5.QtGui.QIcon.fromTheme("application-exit"))

        self.main_tab_switch(0)

    def edit_unit_settings(self):
        settings_window = dialogs.SettingsDialog()
        self.settings = settings_window.exec(self.settings, "Units")

    def edit_activity_data(self):
        edit_activity_dialog = dialogs.EditActivityDialog()
        return_value = edit_activity_dialog.exec(self.activity)
        if not return_value:
            return
        # Delete activity
        if return_value == dialogs.DELETE_ACTIVITY:
            # Must be saved to another variable because self.activity
            # changes when the row is removed
            to_delete = self.activity
            for row in range(len(self.activities)):
                item = self.activity_list_table.item(row, 0)
                if self.activities.get_activity(item.activity_id) is to_delete:
                    self.activity_list_table.removeRow(row)
                    break
            self.activities.remove(to_delete.activity_id)
            return

        self.activity_list_table.setSortingEnabled(False)
        for row in range(len(self.activities)):
            if (
                self.activities.get_activity(
                    self.activity_list_table.item(row, 0).activity_id
                )
                == self.activity
            ):
                self.activity_list_table.set_id_row(
                    self.activity.activity_id,
                    self.activity.unload(activity_list.UnloadedActivity).list_row,
                    row,
                )
                break
        self.activities.update(self.activity.activity_id)
        self.update_activity(row)
        self.activity_list_table.setSortingEnabled(True)

    def update_activity_list(self):
        """Make the activity list show the correct activities."""
        self.activity_list_table.setRowCount(len(self.activities))
        for i, activity in enumerate(self.activities):
            self.activity_list_table.set_id_row(
                activity.activity_id, activity.list_row, i
            )
        self.activity_list_table.resizeColumnsToContents()
        self.activity_list_table.default_sort()

    def add_activity(self, new_activity, position=0):
        """Add an activity to list."""
        activity_id = new_activity.activity_id
        activity_elements = new_activity.unload(activity_list.UnloadedActivity).list_row
        self.activities.add_activity(new_activity)
        self.activity_list_table.add_id_row(activity_id, activity_elements, position)

    def update_splits(self, data):
        """Update the activity splits page."""
        self.split_table.update_data(data)

    def update_page(self, page):
        """Switch to a new activity tab page."""
        if page in self.updated:
            return
        if page == 0:
            # Update labels, map and data box
            self.activity_name_label.setText(self.activity.name)
            self.flags_label.setText(" | ".join(self.activity.active_flags))
            self.description_label.setText(markdown.markdown(self.activity.description))
            self.date_time_label.setText(times.nice(self.activity.start_time))
            self.activity_type_label.setText(self.activity.sport)
            self.info_table.update_data(self.activity.stats)
            if self.activity.track.has_position_data:
                self.map_widget.setVisible(True)
                self.map_widget.show(self.activity.track.lat_lon_list)
            else:
                self.map_widget.setVisible(False)
        elif page == 1:
            # Update charts
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
                self.charts.update_show(
                    "cadence", [self.activity.track.graph("cadence")]
                )
            else:
                self.charts.hide("cadence")
            if "power" in self.activity.track:
                self.charts.update_show("power", [self.activity.track.graph("power")])
            else:
                self.charts.hide("power")
        elif page == 2:
            self.update_splits(
                self.activity.track.splits(
                    splitlength=self.unit_system.units["distance"].size
                )
            )
        elif page == 3:
            zones = (
                activity_types.ZONES[self.activity.sport]
                if self.activity.sport in activity_types.ZONES
                else activity_types.ZONES[None]
            )
            zones = [self.unit_system.decode(x, "speed") for x in zones]
            self.zones_chart.set_zones(zones)
            self.zones_chart.update(self.activity.track.get_zone_durations(zones))
        elif page == 4:
            good_distances = (
                activity_types.SPECIAL_DISTANCES[self.activity.sport]
                if self.activity.sport in activity_types.SPECIAL_DISTANCES
                else activity_types.SPECIAL_DISTANCES[None]
            )
            table, graph = self.activity.track.get_curve(good_distances)
            self.curve_chart.update([graph])
            self.curve_table.update_data(list(good_distances.values()), table)
        self.updated.add(page)

    def update_activity(self, selected):
        """Show a new activity on the right."""
        # Find the correct activity
        self.activity = self.activities.get_activity(
            self.activity_list_table.item(selected, 0).activity_id
        )
        # Previously generated pages need refreshing
        self.updated = set()
        self.update_page(self.activity_tabs.currentIndex())

    def import_activities(self):
        """Import some user-given activities."""
        # [1] gives file type chosen ("Activity Files (...)",
        # "All Files" etc.)
        filenames = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Import an activity", paths.HOME, "Activity Files (*.gpx *.fit)",
        )[0]
        if not filenames:
            return
        self.activity_list_table.setSortingEnabled(False)
        import_progress_dialog = QtWidgets.QProgressDialog(
            "Importing Activities", "Cancel", 0, len(filenames), self
        )
        import_progress_dialog.setWindowModality(Qt.WindowModal)
        for completed, filename in enumerate(filenames):
            import_progress_dialog.setValue(completed)
            self.add_activity(load_activity.import_and_load(filename, paths.TRACKS))
            if import_progress_dialog.wasCanceled():
                break
        else:
            import_progress_dialog.setValue(len(filenames))
        self.activity_list_table.setCurrentCell(0, 0)
        self.activity_list_table.setSortingEnabled(True)

    def export_activity(self):
        if files.has_extension(self.activity.original_name, ".gpx"):
            file_type = "GPX file (*.gpx)"
        elif files.has_extension(self.activity.original_name, ".fit"):
            file_type = "FIT file (*.fit)"
        else:
            file_type = ""
        out_name = files.decode_name(self.activity.original_name)
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Original Activity", f"{paths.HOME}/{out_name}", file_type,
        )[0]

        if not filename:
            return
        self.activity.export_original(filename)

    def main_tab_switch(self, tab):
        if self.main_tabs.tabText(tab) == "Summary":
            self.summary_tab_switch()
        elif self.main_tabs.tabText(tab) == "Activities":
            if not self.activity_list_table.selectedItems():
                self.activity_list_table.selectRow(0)
        else:
            raise ValueError("Invalid tab")

    def summary_tab_switch(self):
        tab = self.summary_tabs.currentIndex()
        if self.summary_tabs.tabText(tab) == "Totals":
            self.update_totals()
        elif self.summary_tabs.tabText(tab) == "Progression":
            self.update_progression()
        else:
            raise ValueError("Invalid tab")

    def update_progression(self):
        allowed_activity_types = self.get_allowed_for_summary()
        data = self.activities.get_progression_data(
            allowed_activity_types, self.summary_period, NOW, lambda a: a.distance
        )
        self.progression_chart.update(
            [((d[0], "date"), (d[1], "distance")) for d in data]
        )
        if self.summary_period == "All Time":
            self.progression_chart.series()
        else:
            self.progression_chart.date_time_axis.setRange(
                times.start_of(NOW, self.summary_period.casefold()),
                times.end_of(NOW, self.summary_period.casefold()),
            )
        if self.summary_period == "Week":
            self.progression_chart.date_time_axis.setTickCount(8)
            self.progression_chart.date_time_axis.setFormat("dddd")
        if self.summary_period == "Month":
            self.progression_chart.date_time_axis.setTickCount(32)
            self.progression_chart.date_time_axis.setFormat("d")
        if self.summary_period == "Year":
            self.progression_chart.date_time_axis.setTickCount(13)
            self.progression_chart.date_time_axis.setFormat("MMMM")

    def handle_summary_check(self, item):
        """Get the right check-boxes selected."""
        if self.do_not_recurse:
            return
        self.do_not_recurse = True
        if item.text() == "All" and item.checkState() != Qt.PartiallyChecked:
            for i in range(len(activity_types.TYPES)):
                self.activity_types_list.item(i + 1).setCheckState(item.checkState())
        else:
            states = set(
                self.activity_types_list.item(i + 1).checkState()
                for i in range(len(activity_types.TYPES))
            )
            if len(states) == 1:
                new_state = next(iter(states))
            else:
                new_state = Qt.PartiallyChecked
            self.activity_types_list.item(0).setCheckState(new_state)
        self.do_not_recurse = False
        self.summary_tab_switch()

    def handle_summary_double_click(self, item):
        """Select this item only."""
        if item.text() == "All":
            self.activity_types_list.item(0).setCheckState(Qt.Checked)
            return
        self.do_not_recurse = True
        self.activity_types_list.item(0).setCheckState(Qt.PartiallyChecked)
        for i in range(len(activity_types.TYPES)):
            this_item = self.activity_types_list.item(i + 1)
            this_item.setCheckState(Qt.Checked if this_item is item else Qt.Unchecked)
        self.do_not_recurse = False
        self.summary_tab_switch()

    def get_allowed_for_summary(self):
        """Get the allowed activity types from the checklist."""
        allowed_activity_types = set()
        for i, a in enumerate(activity_types.TYPES):
            if self.activity_types_list.item(i + 1).checkState() == Qt.Checked:
                allowed_activity_types.add(a)
        return allowed_activity_types

    def set_formatted_number_label(self, label, value, dimension):
        """Set a label to a number, formatted with the correct units."""
        label.setText(
            number_formats.default_as_string(self.unit_system.format(value, dimension))
        )

    def update_totals(self):
        """Update the summary page totals."""
        allowed_activity_types = self.get_allowed_for_summary()
        self.set_formatted_number_label(
            self.total_distance_label,
            self.activities.total_distance(
                allowed_activity_types, self.summary_period, NOW
            ),
            "distance",
        )
        self.set_formatted_number_label(
            self.total_time_label,
            self.activities.total_time(
                allowed_activity_types, self.summary_period, NOW
            ),
            "time",
        )
        self.total_activities_label.setText(
            str(
                self.activities.total_activities(
                    allowed_activity_types, self.summary_period, NOW
                )
            )
        )
        self.set_formatted_number_label(
            self.total_climb_label,
            self.activities.total_climb(
                allowed_activity_types, self.summary_period, NOW
            ),
            "altitude",
        )

    def summary_period_changed(self, value):
        self.summary_period = value
        self.summary_tab_switch()

    @property
    def unit_system(self):
        return units.UNIT_SYSTEMS[self.settings.unit_system]

    def closeEvent(self, event):
        self.activities.save()
        return super().closeEvent(event)


def main():
    """Run the app and display the main window."""
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(PyQt5.QtGui.QIcon("resources/icons/icon.png"))
    main_window = MainWindow(activity_list.from_disk())

    main_window.show()
    sys.exit(app.exec_())
