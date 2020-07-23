#!/usr/bin/env python3
import collections
import datetime
import sys

import markdown
import PyQt5
import PyQt5.uic
import pyqtlet
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

import activity_list
import activity_types
import charts
import files
import load_activity
import number_formats
import settings
import times
import units


UNIVERSAL_FLAGS = ("Commute", "Indoor")
TYPE_FLAGS = collections.defaultdict(tuple)
TYPE_FLAGS.update(activity_types.FLAGS)
DELETE_ACTIVITY = 222  # 0xDE[lete]

NOW = datetime.datetime.now()


def default_map_location(route):
    """Calculate the mean position for centering the map."""
    return [
        (min(p[component] for p in route) + max(p[component] for p in route)) / 2
        for component in range(2)
    ]


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PyQt5.uic.loadUi("settings.ui", self)

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
        new_settings = self.get_settings()
        new_settings.save()
        return new_settings


class EditActivityDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PyQt5.uic.loadUi("edit_activity.ui", self)
        self.type_edit.addItems(activity_types.TYPES)
        self.delete_activity_button.setIcon(PyQt5.QtGui.QIcon.fromTheme("edit-delete"))

    def update_flags(self):
        """Generate the flags in the list based on the activity."""
        if "activity" not in vars(self):
            return
        self.flags = TYPE_FLAGS[self.type_edit.currentText()] + UNIVERSAL_FLAGS
        self.flag_list.clear()
        self.flag_list.addItems(self.flags)
        for i, flag in enumerate(self.flags):
            self.flag_list.item(i).setCheckState(
                Qt.Checked
                if flag in self.activity.flags and self.activity.flags[flag]
                else Qt.Unchecked
            )

    def load_from_activity(self):
        """Load an self.activity's data to the UI."""
        self.name_edit.setText(self.activity.name)
        self.type_edit.setCurrentText(self.activity.sport)
        self.description_edit.setPlainText(self.activity.description)
        self.update_flags()

    def apply_to_activity(self):
        """Apply the settings to an self.activity."""
        self.activity.name = self.name_edit.text()
        self.activity.sport = self.type_edit.currentText()
        self.activity.description = self.description_edit.toPlainText()
        for i, flag in enumerate(self.flags):
            self.activity.flags[flag] = (
                self.flag_list.item(i).checkState() == Qt.Checked
            )

        self.activity.save()

    def handle_delete_button(self):
        confirm_box = QtWidgets.QMessageBox()
        confirm_box.setText(f"Are you sure you want to delete {self.activity.name}?")
        confirm_box.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        result = confirm_box.exec()
        if result == QtWidgets.QMessageBox.Yes:
            self.done(DELETE_ACTIVITY)

    def exec(self, activity):
        self.activity = activity
        self.load_from_activity()
        result = super().exec()
        if result and result != DELETE_ACTIVITY:
            self.apply_to_activity()
        return result


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, activities, *args, **kwargs):
        self.activities = activities
        super(MainWindow, self).__init__(*args, **kwargs)

        PyQt5.uic.loadUi("main.ui", self)
        self.updated = set()

        self.settings = settings.load_settings()

        self.activity_list_table.unit_system = self.unit_system
        self.split_table.unit_system = self.unit_system
        self.info_table.unit_system = self.unit_system
        self.curve_table.unit_system = self.unit_system

        self.update_activity_list()

        # Set up map
        self.map_widget = pyqtlet.MapWidget()
        self.map_widget.setContextMenuPolicy(Qt.NoContextMenu)
        self.map = pyqtlet.L.map(self.map_widget, {"attributionControl": False})
        self.map_container.addWidget(self.map_widget)
        self.map.setView([51, -1], 14)
        pyqtlet.L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png").addTo(self.map)

        # Set activity list heading resize modes
        header = self.activity_list_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

        # Disable resizing in activity list
        self.activity_list_table.resize_to_contents("v")
        self.split_table.resize_to_contents("h")

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
        settings_window = SettingsDialog()
        self.settings = settings_window.exec(self.settings, "Units")

    def edit_activity_data(self):
        edit_activity_dialog = EditActivityDialog()
        return_value = edit_activity_dialog.exec(self.activity)
        if not return_value:
            return
        # Delete activity
        if return_value == DELETE_ACTIVITY:
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
                self.assign_activity_items(
                    self.activity.activity_id,
                    self.activity.create_unloaded().list_row,
                    row,
                )
                break
        self.activities.update(self.activity.activity_id)
        self.update_activity(row)
        self.activity_list_table.setSortingEnabled(True)

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
            self.info_table.set_item(i, 0, k)
            self.info_table.set_item(
                i,
                1,
                v,
                number_formats.info_format(k),
                align=Qt.AlignRight | Qt.AlignVCenter,
            )
            self.info_table.set_item(
                i,
                2,
                self.unit_system.units[v.dimension].symbol,
                align=Qt.AlignLeft | Qt.AlignVCenter,
            )

    def update_activity_list(self):
        """Make the activity list show the correct activities."""
        self.activity_list_table.setRowCount(len(self.activities))
        for i, activity in enumerate(self.activities):
            self.assign_activity_items(activity.activity_id, activity.list_row, row=i)
        self.activity_list_table.resizeColumnsToContents()
        self.activity_list_table.sortItems(2, Qt.DescendingOrder)

    def add_activity(self, new_activity, position=0):
        """Add an activity to list."""
        activity_id = new_activity.activity_id
        activity_elements = new_activity.create_unloaded().list_row
        self.activity_list_table.insertRow(position)
        self.activities.add_activity(new_activity)
        self.assign_activity_items(activity_id, activity_elements, position)

    def assign_activity_items(self, activity_id, activity_elements, row=0):
        """
        Set the items in the given activity list row to specific values.

        Assigns values to a row, formatting (value, dimension) tuples
        properly.
        """
        formats = [
            number_formats.list_format(self.activity_list_table.get_heading(j))
            for j in range(len(activity_elements))
        ]
        self.activity_list_table.set_row(activity_id, activity_elements, row, formats)

    def update_splits(self, data):
        """Update the activity splits page."""
        self.split_table.setRowCount(len(data))
        for y, row in enumerate(data):
            row_data = [y + 1] + row
            formats = [
                number_formats.split_format(self.split_table.get_heading(x))
                for x in range(len(row_data))
            ]
            self.split_table.set_row(
                row_data, y, formats, alignments=Qt.AlignRight | Qt.AlignVCenter
            )

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
            self.add_info(self.activity.stats)
            self.show_on_map(self.activity.track.lat_lon_list)
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
            print(zones)
            zones = [self.unit_system.decode(x, "speed") for x in zones]
            print(zones)
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
            for index, row in enumerate(table):
                self.curve_table.setRowCount(len(table))
                self.curve_table.set_row(
                    row,
                    index,
                    (
                        lambda x: good_distances[
                            round(self.unit_system.decode(x, "distance"), 8)
                        ],
                        lambda x: times.to_string(x),
                    ),
                )
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
            self,
            "Import an activity",
            PyQt5.QtCore.QDir.homePath(),
            "Activity Files (*.gpx *.fit)",
        )[0]
        if not filenames:
            return
        self.activity_list_table.setSortingEnabled(False)
        for filename in filenames:
            self.add_activity(load_activity.import_and_load(filename))
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
            self,
            "Export Original Activity",
            f"{PyQt5.QtCore.QDir.homePath()}/{out_name}",
            file_type,
        )[0]

        if not filename:
            return
        self.activity.export_original(filename)

    def main_tab_switch(self, tab):
        if self.main_tabs.tabText(tab) == "Summary":
            self.summary_tab_switch()
        elif self.main_tabs.tabText(tab) == "Activities":
            if not self.activity_list_table.selectedItems():
                self.activity_list_table.setCurrentCell(0, 0)
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
    main_window = MainWindow(activity_list.from_disk())

    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
