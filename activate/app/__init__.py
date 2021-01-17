import sys
from pathlib import Path

import pkg_resources
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon, QPixmap

import activate.app.dialogs
import activate.app.dialogs.activity
import activate.app.dialogs.settings
from activate import (
    activity,
    activity_list,
    files,
    load_activity,
    serialise,
    track,
    units,
)
from activate.app import activity_view, connect, maps, paths, settings
from activate.app.ui.main import Ui_main_window


class MainWindow(QtWidgets.QMainWindow, Ui_main_window):
    def __init__(self, activities, *args, **kwargs):
        self.activities = activities
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        paths.ensure_all_present()

        self.settings = settings.load_settings()
        self.main_tabs.setTabVisible(2, bool(self.settings.servers))

        # Create a global map widget to be used everywhere. This is
        # necessary because pyqtlet doesn't support multiple L.map
        # instances.
        self.map_widget = maps.MapWidget(self)

        self.activity_summary.setup(self.unit_system, self.map_widget)
        self.social_activity_summary.setup(self.unit_system, self.map_widget)
        self.summary.setup(self.unit_system, self.map_widget, self.activities)
        self.activity_list_table.set_units(self.unit_system)
        self.social_activity_list.set_units(self.unit_system)
        self.activity_list_table.set_units(self.unit_system)

        self.update_activity_list()
        self.activity_list_table.right_clicked.connect(self.activity_list_menu)
        self.summary.records_table.gone_to.connect(self.show_activity)

        for widget, icon_name in (
            (self.action_import, "document-open"),
            (self.action_add_manual, "document-new"),
            (self.action_edit, "document-edit"),
            (self.action_analyse, "view-statistics"),
            (self.action_add_photos, "insert-image"),
            (self.action_units, "measure"),
            (self.action_servers, "network-server"),
            (self.export_menu, "document-send"),
            (self.action_quit, "application-exit"),
        ):
            widget.setIcon(QIcon.fromTheme(icon_name))

        self.main_tab_switch(0)

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
        cell = self.social_activity_list.item(selected, 0)
        if cell is None:
            return
        activity_id = cell.activity_id
        self.setUpdatesEnabled(False)
        try:
            self.social_activity = self.social_activities.get_activity(activity_id)
        except ValueError:
            server = next(
                s
                for s in self.settings.servers
                if s.name
                in self.social_activities.by_id(activity_id).server.split("\n")
            )
            self.social_activity = activity.Activity(
                **serialise.load_bytes(
                    server.get_data(f"get_activity/{activity_id}"), gz=True
                )
            )
            self.social_activities.provide_full_activity(
                activity_id, self.social_activity
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
            "Activity Files (*.gpx *.fit *.tcx *.gpx.gz *.fit.gz *.tcx.gz)",
        )[0]
        if not filenames:
            return
        self.activity_list_table.setSortingEnabled(False)
        for filename in activate.app.dialogs.progress(
            self, filenames, "Importing Activities"
        ):
            filename = Path(filename)
            try:
                self.add_activity(load_activity.import_and_load(filename, paths.TRACKS))
            except Exception as e:
                alert_box = QtWidgets.QMessageBox()
                alert_box.setText(f"Could not load {filename}:\n{e}")
                alert_box.exec()

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
            self.summary.update_activity_types_list()

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
        """Open a seperate window for activity analysis."""
        self.activity_view = activity_view.ActivityView()
        self.activity_view.setup(self.unit_system, self.map_widget)
        try:
            activity = (
                self.activity
                if self.main_tabs.tabText(self.main_tabs.currentIndex()) == "Activities"
                else self.social_activity
            )
        except AttributeError:
            return
        self.activity_view.show_activity(activity)
        self.activity_view.closed.connect(self.activity_view_closed)
        self.activity_view.create()
        self.activity_view.showMaximized()

    def activity_view_closed(self):
        self.activity_summary.show_map()
        self.map_widget.remove_marker()
        self.map_widget.remove_highlight()

    def main_tab_switch(self, tab):
        """
        Switch between the main tabs at the top.

        Triggers the opened tab to update.
        """
        tab_name = self.main_tabs.tabText(tab)
        for action in (self.action_edit, self.action_add_photos, self.export_menu):
            action.setEnabled(tab_name == "Activities")
        self.activity_menu.setEnabled(tab_name != "Summary")
        if tab_name == "Summary":
            self.summary.summary_tab_switch()
        elif tab_name == "Activities":
            self.activity_summary.show_map()
            if not self.activity_list_table.selectedItems():
                self.activity_list_table.selectRow(0)
        elif tab_name == "Social":
            self.social_activity_summary.show_map()
            self.social_tab_update()
        else:
            raise ValueError("Invalid tab")

    def get_social_activities(self):
        """
        Download all activities from each server.

        Gets the activity list from the server, and then downloads each
        activity. Also uploads missing activities.
        """
        self.social_activities = activity_list.ActivityList([], None)
        for server in activate.app.dialogs.progress(
            self, self.settings.servers, f"Downloading activities"
        ):
            try:
                server_activities = activity_list.from_serial(
                    serialise.load_bytes(server.get_data("get_activities")), None
                )
            except connect.requests.RequestException:
                continue
            own_ids = set(a.activity_id for a in self.activities)
            for activity_ in server_activities:
                activity_.server = server.name
                if activity_.username == server.username:
                    aid = activity_.activity_id
                    if aid not in own_ids:
                        server.get_data(f"delete_activity/{aid}")
                        continue
                    own_ids.remove(aid)
                try:
                    previous = self.social_activities.by_id(activity_.activity_id)
                    previous.server += f"\n{activity_.server}"
                    previous.username += f"\n{activity_.username}"
                except KeyError:
                    self.social_activities.append(activity_)
            if not own_ids:
                continue
            progress = activate.app.dialogs.progress(
                self, own_ids, f"Syncing activities with {server.name}"
            )
            for missing_id in progress:
                try:
                    server.upload_activity(self.activities.get_activity(missing_id))
                except connect.requests.RequestException:
                    for _ in progress:
                        pass
                    break

    def social_tab_update(self):
        self.get_social_activities()
        self.social_tree.set_servers(self.settings.servers, self.social_activities)
        self.social_activity_list.setUpdatesEnabled(False)
        self.social_activity_list.setSortingEnabled(False)
        self.social_activity_list.setRowCount(0)
        self.social_activity_list.setRowCount(len(self.social_activities))
        for row, activity_ in enumerate(self.social_activities):
            self.social_activity_list.set_id_row(
                activity_.activity_id, activity_.list_row, row
            )
        self.filter_social_activities()
        self.social_activity_list.resizeColumnsToContents()
        self.social_activity_list.default_sort()

    def filter_social_activities(self):
        self.social_activity_list.setUpdatesEnabled(False)
        self.social_activity_list.filter_by_server(
            self.social_tree.get_enabled_servers()
        )
        self.social_activity_list.setUpdatesEnabled(True)

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
    icon = QPixmap()
    icon.loadFromData(
        pkg_resources.resource_string("activate.resources", "icons/icon.png")
    )
    app.setWindowIcon(QIcon(icon))
    app.setApplicationName("Activate")
    main_window = MainWindow(activity_list.from_disk(paths.DATA))

    main_window.showMaximized()
    sys.exit(app.exec())
