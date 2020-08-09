#!/usr/bin/env python3
import datetime
import sys

import markdown
import PyQt5
import PyQt5.uic
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from activate.app import activity_list, charts, dialogs, maps, paths, photos, settings
from activate.core import (
    activity,
    activity_types,
    files,
    load_activity,
    number_formats,
    times,
    track,
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

        for table in (
            self.activity_list_table,
            self.split_table,
            self.info_table,
            self.curve_table,
        ):
            table.set_units(self.unit_system)

        self.update_activity_list()

        self.map_widget = maps.RouteMap(self.map_container)
        size_policy = self.map_widget.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        self.map_widget.setSizePolicy(size_policy)

        self.photo_list = photos.PhotoList(self)
        self.overview_tab_layout.addWidget(self.photo_list, 1, 1)

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

        self.progression_chart = charts.DateTimeLineChart(
            self.progression_graph, self.unit_system, series_count=5, vertical_ticks=8
        )

        self.summary_period = "All Time"

        # Set up activity types list for the summary page
        self.activity_types_list.row_names = list(activity_types.TYPES)
        self.activity_types_list.add_all_row()
        self.activity_types_list.check_all()

        self.action_import.setIcon(QIcon.fromTheme("document-open"))
        self.action_add_manual.setIcon(QIcon.fromTheme("document-new"))
        self.action_edit.setIcon(QIcon.fromTheme("document-edit"))
        self.action_add_photos.setIcon(QIcon.fromTheme("insert-image"))
        self.export_menu.setIcon(QIcon.fromTheme("document-send"))
        self.action_quit.setIcon(QIcon.fromTheme("application-exit"))

        self.main_tab_switch(0)

    def edit_unit_settings(self):
        settings_window = dialogs.SettingsDialog()
        self.settings = settings_window.exec(self.settings, "Units")

    def add_manual_activity(self):
        manual_window = dialogs.ManualActivityDialog()
        data = manual_window.exec({})
        if data:
            self.add_activity(
                activity.Activity(
                    data["Name"],
                    data["Type"],
                    track.ManualTrack(
                        data["Start Time"],
                        data["Distance"] * 1000,
                        data["Ascent"],
                        data["Duration"],
                    ),
                    "[manual]",
                    data["Flags"],
                    data["Start Time"],
                    data["Distance"] * 1000,
                    description=data["Description"],
                )
            )

    def edit_activity_data(self):
        edit_activity_dialog = (
            dialogs.EditManualActivityDialog()
            if self.activity.track.manual
            else dialogs.EditActivityDialog()
        )
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

    def add_photos(self):
        filenames = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Add photos",
            paths.HOME,
            "Image files (*.png *.jpg *.jpeg *.gif *.bmp *.ppm *.pgm *.xpm)",
        )[0]
        if not filenames:
            return

        for filename in filenames:
            self.activity.photos.append(
                files.copy_to_location_renamed(filename, paths.PHOTOS)
            )
        self.activity.save(paths.ACTIVITIES)

    def update_activity_list(self):
        """Make the activity list show the correct activities."""
        self.activity_list_table.setRowCount(len(self.activities))
        for i, activity_ in enumerate(self.activities):
            self.activity_list_table.set_id_row(
                activity_.activity_id, activity_.list_row, i
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
        else:
            self.map_widget.setVisible(False)
        self.photo_list.replace_photos(self.activity.photos)

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

    def update_activity(self, selected):
        """Show a new activity on the right."""
        # Find the correct activity
        self.setUpdatesEnabled(False)
        self.activity = self.activities.get_activity(
            self.activity_list_table.item(selected, 0).activity_id
        )
        if self.activity.track.manual:
            self.activity_tabs.setCurrentIndex(0)
        for page in range(1, 5):
            self.activity_tabs.setTabEnabled(page, not self.activity.track.manual)
        # Previously generated pages need refreshing
        self.updated = set()
        self.update_page(self.activity_tabs.currentIndex())
        self.setUpdatesEnabled(True)

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
        tab_name = self.main_tabs.tabText(tab)
        for action in (self.export_menu, self.activity_menu):
            action.setEnabled(tab_name == "Activities")
        if tab_name == "Summary":
            self.summary_tab_switch()
        elif tab_name == "Activities":
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
        x_axis = self.progression_chart.date_time_axis
        if self.summary_period != "All Time":
            x_axis.setRange(
                times.start_of(NOW, self.summary_period.casefold()),
                times.end_of(NOW, self.summary_period.casefold()),
            )
        if self.summary_period == "Week":
            x_axis.setTickCount(8)
            x_axis.setFormat("dddd")
        if self.summary_period == "Month":
            x_axis.setTickCount(32)
            x_axis.setFormat("d")
        if self.summary_period == "Year":
            x_axis.setTickCount(13)
            x_axis.setFormat("MMMM")

    def get_allowed_for_summary(self):
        """Get the allowed activity types from the checklist."""
        return set(self.activity_types_list.checked_rows)

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
    app.setWindowIcon(QIcon("resources/icons/icon.png"))
    main_window = MainWindow(activity_list.from_disk())

    main_window.show()
    sys.exit(app.exec_())
