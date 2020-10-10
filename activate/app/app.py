#!/usr/bin/env python3
import datetime
import sys
from collections import Counter

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

import activate.app.dialogs.activity
import activate.app.dialogs.settings
from activate.app import activity_list, charts, connect, maps, paths, settings
from activate.app.ui.main import Ui_main_window
from activate.core import (
    activity,
    activity_types,
    files,
    load_activity,
    number_formats,
    serialise,
    track,
    units,
)

NOW = datetime.datetime.now()
PROGRESSION_Y_OPTIONS = {
    "Distance": (lambda a: a.distance, "distance"),
    "Time": (lambda a: a.duration.total_seconds(), "real_time"),
    "Climb": (lambda a: a.climb, "altitude"),
}


class MainWindow(QtWidgets.QMainWindow, Ui_main_window):
    def __init__(self, activities, *args, **kwargs):
        self.activities = activities
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.settings = settings.load_settings()

        self.main_tabs.setTabVisible(2, bool(self.settings.servers))

        # Create a global map widget to be used everywhere. This is
        # necessary because pyqtlet doesn't support multiple L.map
        # instances.
        self.map_widget = maps.RouteMap(self)

        self.activity_view.setup(self.unit_system, self.map_widget)
        self.social_activity_view.setup(self.unit_system, self.map_widget)
        paths.ensure_all_present()

        self.records_table.set_units(self.unit_system)

        self.activity_list_table.set_units(self.unit_system)
        self.social_activity_list.set_units(self.unit_system)

        self.update_activity_list()
        self.activity_list_table.right_clicked.connect(self.activity_list_menu)

        self.summary_period = "All Time"

        self.progression_chart = charts.TimePeriodLineChart(
            self.progression_graph,
            self.unit_system,
            series_count=5,
            vertical_ticks=8,
            y_axis_label=False,
        )

        self.y_axis_box.addItems(
            [
                self.unit_system.format_name_unit(
                    PROGRESSION_Y_OPTIONS[option][1], name=option
                )
                for option in PROGRESSION_Y_OPTIONS
            ]
        )

        self.update_activity_types_list()

        self.records_table.gone_to.connect(self.show_activity)

        self.social_activities = []

        self.action_import.setIcon(QIcon.fromTheme("document-open"))
        self.action_add_manual.setIcon(QIcon.fromTheme("document-new"))
        self.action_edit.setIcon(QIcon.fromTheme("document-edit"))
        self.action_add_photos.setIcon(QIcon.fromTheme("insert-image"))
        self.action_units.setIcon(QIcon.fromTheme("measure"))
        self.action_servers.setIcon(QIcon.fromTheme("network-server"))
        self.export_menu.setIcon(QIcon.fromTheme("document-send"))
        self.action_quit.setIcon(QIcon.fromTheme("application-exit"))

        self.main_tab_switch(0)

    def update_activity_types_list(self):
        """Set up activity types list for the summary page."""
        self.activity_types_list.row_names = [
            x[0] for x in Counter(a.sport for a in self.activities).most_common()
        ]
        self.activity_types_list.add_all_row()
        self.activity_types_list.check_all()

    def edit_unit_settings(self):
        settings_window = activate.app.dialogs.settings.SettingsDialog()
        self.settings = settings_window.exec(self.settings, "Units")

    def edit_server_settings(self):
        settings_window = activate.app.dialogs.settings.SettingsDialog()
        self.settings = settings_window.exec(self.settings, "Servers")

        self.main_tabs.setTabVisible(2, bool(self.settings.servers))

    def add_manual_activity(self):
        manual_window = activate.app.dialogs.activity.ManualActivityDialog()
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
        for server in self.settings.servers:
            try:
                server.post_data(
                    "send_activity",
                    {"activity": serialise.dump_bytes(new_activity.save_data)},
                )
            except connect.requests.RequestException:
                continue
        self.activity_list_table.add_id_row(activity_id, activity_elements, position)

    def update_activity(self, selected):
        """Show a new activity on the right on the Activities page."""
        self.setUpdatesEnabled(False)
        self.activity = self.activities.get_activity(
            self.activity_list_table.item(selected, 0).activity_id
        )
        self.activity_view.show_activity(self.activity)
        self.setUpdatesEnabled(True)

    def update_social_activity(self, selected):
        """Show a new activity on the right on the Social page."""
        self.setUpdatesEnabled(False)
        self.social_activity = self.social_activities.get_activity(
            self.social_activity_list.item(selected, 0).activity_id
        )
        self.social_activity_view.show_activity(self.social_activity)
        self.setUpdatesEnabled(True)

    def import_activities(self):
        """Import some user-given activities."""
        # [1] gives file type chosen ("Activity Files (...)",
        # "All Files" etc.)
        filenames = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Import an activity", paths.HOME, "Activity Files (*.gpx *.fit *.tcx)"
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
        """Export the original version of the activity."""
        if files.has_extension(self.activity.original_name, ".gpx"):
            file_type = "GPX file (*.gpx)"
        elif files.has_extension(self.activity.original_name, ".fit"):
            file_type = "FIT file (*.fit)"
        elif files.has_extension(self.activity.original_name, ".tcx"):
            file_type = "TCX file (*.TCX)"
        else:
            file_type = ""
        out_name = files.decode_name(self.activity.original_name)
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Original Activity", f"{paths.HOME}/{out_name}", file_type
        )[0]

        if not filename:
            return
        self.activity.export_original(filename)

    def edit_activity_data(self):
        """
        Open the Edit Activity dialog.

        This then edits or deletes the activity as appropriate.
        """
        previous_sport = self.activity.sport
        edit_activity_dialog = (
            activate.app.dialogs.activity.EditManualActivityDialog()
            if self.activity.track.manual
            else activate.app.dialogs.activity.EditActivityDialog()
        )
        return_value = edit_activity_dialog.exec(self.activity)
        if not return_value:
            return
        # Delete activity
        if return_value == activate.app.dialogs.activity.DELETE_ACTIVITY:
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
        if self.activity.sport != previous_sport:
            self.update_activity_types_list()

    def add_photos(self):
        """Open the Add Photos dialog."""
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
        self.activity_view.force_update_page(0)

    def show_activity(self, activity_id):
        self.main_tabs.setCurrentIndex(1)
        self.activity_list_table.select(activity_id)

    def main_tab_switch(self, tab):
        """
        Switch between the main tabs at the top.

        Triggers the opened tab to update.
        """
        tab_name = self.main_tabs.tabText(tab)
        for action in (self.export_menu, self.activity_menu):
            action.setEnabled(tab_name == "Activities")
        if tab_name == "Summary":
            self.summary_tab_switch()
        elif tab_name == "Activities":
            self.activity_view.show_map()
            if not self.activity_list_table.selectedItems():
                self.activity_list_table.selectRow(0)
        elif tab_name == "Social":
            self.social_activity_view.show_map()
            self.social_tab_update()
        else:
            raise ValueError("Invalid tab")

    def summary_tab_switch(self):
        tab = self.summary_tabs.tabText(self.summary_tabs.currentIndex())
        {
            "Totals": self.update_totals,
            "Records": self.update_records,
            "Progression": self.update_progression,
            "Gallery": self.update_gallery,
        }[tab]()

    def update_progression(self):
        """Update the progression chart."""
        allowed_activity_types = self.get_allowed_for_summary()
        periods, data = self.activities.get_progression_data(
            allowed_activity_types,
            self.summary_period,
            NOW,
            PROGRESSION_Y_OPTIONS[self.progression_y_option][0],
        )
        if self.summary_period == "All Time":
            self.progression_chart.period_axis.mode = "auto"
            self.progression_chart.remove_legend()
        else:
            self.progression_chart.period_axis.mode = {
                "Year": "month",
                "Month": "day",
                "Week": "weekday",
            }[self.summary_period]
            self.progression_chart.add_legend(periods)
        self.progression_chart.update(
            [
                (
                    (d[0], "date"),
                    (d[1], PROGRESSION_Y_OPTIONS[self.progression_y_option][1]),
                )
                for d in data
            ]
        )

    def change_progression_y(self, new_value):
        for option in PROGRESSION_Y_OPTIONS:
            if option in new_value:
                self.progression_y_option = option
        self.update_progression()

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

    def update_records(self):
        good_distances = {}
        for sport in self.get_allowed_for_summary():
            good_distances.update(
                activity_types.SPECIAL_DISTANCES[sport]
                if sport in activity_types.SPECIAL_DISTANCES
                else activity_types.SPECIAL_DISTANCES[None]
            )
        good_distances = {k: good_distances[k] for k in sorted(good_distances)}
        records, activity_ids = self.activities.get_records(
            self.get_allowed_for_summary(), self.summary_period, NOW, good_distances
        )

        self.records_table.update_data(
            list(good_distances.values()), records, activity_ids
        )

    def update_gallery(self):
        self.gallery.replace_photos(
            self.activities.get_all_photos(
                self.get_allowed_for_summary(), self.summary_period, NOW
            )
        )

    def summary_period_changed(self, value):
        self.summary_period = value
        self.summary_tab_switch()

    def get_social_activities(self):
        """
        Download all activities from each server.

        Gets the activity list from the server, and then downloads each
        activity.
        """
        self.social_activities = activity_list.ActivityList([])
        for server in self.settings.servers:
            try:
                social_ids = serialise.load_bytes(server.get_data("get_activities"))
            except connect.requests.RequestException:
                continue
            for social_id in social_ids:
                data = serialise.load_bytes(
                    server.get_data(f"get_activity/{social_id}")
                )
                data["server"] = server.name
                activity_ = activity.Activity(**data)
                self.social_activities.add_activity(activity_)

    def social_tab_update(self):
        self.get_social_activities()
        self.social_tree.set_servers(self.settings.servers, self.social_activities)
        self.social_activity_list.setRowCount(len(self.social_activities))
        for row, activity_ in enumerate(self.social_activities):
            self.social_activity_list.set_id_row(
                activity_.activity_id, activity_.list_row, row
            )

    def filter_social_activities(self):
        self.social_activity_list.filter_by_server(
            self.social_tree.get_enabled_servers()
        )

    @property
    def unit_system(self):
        system = units.UNIT_SYSTEMS[self.settings.unit_system]
        for dimension, unit in self.settings.custom_units.items():
            unit = units.UNIT_NAMES[unit]
            system.units[dimension] = unit
        return system

    def activity_list_menu(self, event):
        self.activity_menu.exec(event.globalPos())

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
