import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import activate.app.dialogs.activity
import activate.app.dialogs.settings
from activate.app import (
    activity_list,
    activity_view,
    charts,
    connect,
    maps,
    paths,
    settings,
)
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
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

NOW = datetime.now()


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
        self.map_widget = maps.MapWidget(self)

        # This has to be added here so when the heatmap is switched to,
        # the widget is already 'there', so it has a size. This lets
        # fitBounds work properly.
        self.heatmap_layout.addWidget(self.map_widget)

        self.activity_summary.setup(self.unit_system, self.map_widget)
        self.social_activity_summary.setup(self.unit_system, self.map_widget)
        paths.ensure_all_present()

        self.records_table.set_units(self.unit_system)

        self.activity_list_table.set_units(self.unit_system)
        self.social_activity_list.set_units(self.unit_system)

        self.update_activity_list()
        self.activity_list_table.right_clicked.connect(self.activity_list_menu)

        self.summary_period = "All Time"
        self.progression_chart.set_units(self.unit_system)

        self.update_activity_types_list()

        self.records_table.gone_to.connect(self.show_activity)

        self.eddington_chart = charts.LineChart(
            self.eddington_chart_widget, self.unit_system, series_count=2
        )
        self.eddington_chart.y_axis.setTitleText("Count")
        self.eddington_chart.add_legend(("Done", "Target"))
        self.activity_list_table.set_units(self.unit_system)

        self.social_activities = []

        self.action_import.setIcon(QIcon.fromTheme("document-open"))
        self.action_add_manual.setIcon(QIcon.fromTheme("document-new"))
        self.action_edit.setIcon(QIcon.fromTheme("document-edit"))
        self.action_analyse.setIcon(QIcon.fromTheme("view-statistics"))
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
                server.upload_activity(new_activity)
            except connect.requests.RequestException:
                continue
        self.activity_list_table.add_id_row(activity_id, activity_elements, position)

    def update_activity(self, selected):
        """Show a new activity on the right on the Activities page."""
        self.setUpdatesEnabled(False)
        self.activity = self.activities.get_activity(
            self.activity_list_table.item(selected, 0).activity_id
        )
        self.activity_summary.show_activity(self.activity)
        self.setUpdatesEnabled(True)

    def update_social_activity(self, selected):
        """Show a new activity on the right on the Social page."""
        self.setUpdatesEnabled(False)
        self.social_activity = self.social_activities.get_activity(
            self.social_activity_list.item(selected, 0).activity_id
        )
        self.social_activity_summary.show_activity(self.social_activity)
        self.setUpdatesEnabled(True)

    def import_activities(self):
        """Import some user-given activities."""
        # [1] gives file type chosen ("Activity Files (...)",
        # "All Files" etc.)
        filenames = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Import an activity",
            str(paths.HOME),
            "Activity Files (*.gpx *.fit *.tcx)",
        )[0]
        if not filenames:
            return
        self.activity_list_table.setSortingEnabled(False)
        import_progress_dialog = QtWidgets.QProgressDialog(
            "Importing Activities", "Cancel", 0, len(filenames), self
        )
        import_progress_dialog.setWindowModality(Qt.WindowModal)
        for completed, filename in enumerate(filenames):
            filename = Path(filename)
            import_progress_dialog.setValue(completed)
            self.add_activity(load_activity.import_and_load(filename, paths.TRACKS))
            if import_progress_dialog.wasCanceled():
                break
        else:
            import_progress_dialog.setValue(len(filenames))
        self.activity_list_table.setCurrentCell(0, 0)
        self.activity_list_table.setSortingEnabled(True)
        self.main_tab_switch(self.main_tabs.currentIndex())

    def export_activity(self):
        """Export the original version of the activity."""
        if files.has_extension(self.activity.original_name, ".gpx"):
            file_type = "GPX file (*.gpx)"
        elif files.has_extension(self.activity.original_name, ".fit"):
            file_type = "FIT file (*.fit)"
        elif files.has_extension(self.activity.original_name, ".tcx"):
            file_type = "TCX file (*.tcx)"
        else:
            file_type = ""
        out_name = files.decode_name(self.activity.original_name)
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Original Activity", str(paths.HOME / out_name), file_type
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
            for server in self.settings.servers:
                try:
                    server.get_data(
                        f"delete_activity/{to_delete.activity_id}",
                    )
                except connect.requests.RequestException:
                    continue
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

        for server in self.settings.servers:
            try:
                server.upload_activity(self.activity)
            except connect.requests.RequestException:
                continue

    def add_photos(self):
        """Open the Add Photos dialog."""
        filenames = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Add photos",
            str(paths.HOME),
            "Image files (*.png *.jpg *.jpeg *.gif *.bmp *.ppm *.pgm *.xpm)",
        )[0]
        if not filenames:
            return

        for filename in filenames:
            self.activity.photos.append(
                files.copy_to_location_renamed(Path(filename), paths.PHOTOS)
            )
        self.activity.save(paths.ACTIVITIES)
        self.activity_summary.update()

    def show_activity(self, activity_id):
        self.main_tabs.setCurrentIndex(1)
        self.activity_list_table.select(activity_id)

    def analyse_activity(self):
        self.activity_view = activity_view.ActivityView()
        self.activity_view.setup(self.unit_system, self.map_widget)
        self.activity_view.show_activity(self.activity)
        self.activity_view.closed.connect(self.activity_view_closed)
        self.activity_view.create()
        self.activity_view.show()

    def activity_view_closed(self):
        self.activity_summary.show_map()
        self.map_widget.remove_marker()

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
            self.activity_summary.show_map()
            if not self.activity_list_table.selectedItems():
                self.activity_list_table.selectRow(0)
        elif tab_name == "Social":
            self.social_activity_summary.show_map()
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
            "Heatmap": self.update_heatmap,
            "Eddington": self.update_eddington,
        }[tab]()

    def update_progression(self):
        """Update the progression chart."""
        self.progression_chart.update(
            self.summary_period,
            self.get_allowed_for_summary(),
            now=NOW,
            activities=self.activities,
        )

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
        allowed_activities = list(
            self.activities.filtered(allowed_activity_types, self.summary_period, NOW)
        )
        self.set_formatted_number_label(
            self.total_distance_label,
            self.activities.total_distance(allowed_activities),
            "distance",
        )
        self.set_formatted_number_label(
            self.total_time_label,
            self.activities.total_time(allowed_activities),
            "time",
        )
        self.total_activities_label.setText(
            str(self.activities.total_activities(allowed_activities))
        )
        self.set_formatted_number_label(
            self.total_climb_label,
            self.activities.total_climb(allowed_activities),
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

    def update_heatmap(self):
        self.heatmap_layout.addWidget(self.map_widget)
        self.map_widget.show_heatmap(
            self.activities.get_all_routes(
                self.get_allowed_for_summary(), self.summary_period, NOW
            )
        )

    def update_eddington(self):
        allowed_activities = list(
            self.activities.filtered(
                self.get_allowed_for_summary(), self.summary_period, NOW
            )
        )
        unit = self.unit_system.units["distance"].size
        eddington_data = self.activities.eddington(allowed_activities, unit)
        eddington_number = 0
        for eddington_number in range(1, len(eddington_data) + 1):
            if eddington_data[eddington_number - 1] <= eddington_number * unit:
                break
        self.total_eddington_label.setText(
            f"{eddington_number} {self.unit_system.units['distance'].symbol}"
        )
        y_indices = list(range(1, len(eddington_data) + 1))
        x_indices = [x * unit for x in y_indices[: int(eddington_data[0] / unit) + 1]]
        y_indices = (y_indices, None)
        self.eddington_chart.update(
            (
                ((eddington_data, "distance"), y_indices),
                ((x_indices, "distance"), y_indices),
            )
        )

    def summary_period_changed(self, value):
        self.summary_period = value
        self.summary_tab_switch()

    def get_social_activities(self):
        """
        Download all activities from each server.

        Gets the activity list from the server, and then downloads each
        activity. Also uploads missing activities.
        """
        self.social_activities = activity_list.ActivityList([])
        for server in self.settings.servers:
            try:
                social_ids = serialise.load_bytes(server.get_data("get_activities"))
            except connect.requests.RequestException:
                continue
            own_ids = set(a.activity_id for a in self.activities)
            for social_id in social_ids:
                data = serialise.load_bytes(
                    server.get_data(f"get_activity/{social_id}")
                )
                data["server"] = server.name
                activity_ = activity.Activity(**data)
                if activity_.username == server.username:
                    if social_id not in own_ids:
                        server.get_data(f"delete_activity/{social_id}")
                        continue
                    own_ids.remove(social_id)
                self.social_activities.add_activity(activity_)
            if not own_ids:
                continue
            sync_progress_dialog = QtWidgets.QProgressDialog(
                f"Syncing activities with {server.name}",
                "Cancel",
                0,
                len(own_ids),
                self,
            )
            for completed, missing_id in enumerate(own_ids):
                sync_progress_dialog.setValue(completed)
                try:
                    server.upload_activity(self.activities.get_activity(missing_id))
                except connect.requests.RequestException:
                    continue
                if sync_progress_dialog.wasCanceled():
                    break
            else:
                sync_progress_dialog.setValue(len(own_ids))

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
