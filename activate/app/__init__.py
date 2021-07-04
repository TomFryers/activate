import sys
import time
from contextlib import suppress
from pathlib import Path

import pkg_resources
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap

import activate.app.dialogs
import activate.app.dialogs.activity
import activate.app.dialogs.settings
from activate import (
    activity,
    activity_list,
    files,
    filetypes,
    load_activity,
    serialise,
    track,
    units,
)
from activate.app import activity_view, connect, maps, paths, settings, sync, widgets
from activate.app.ui.main import Ui_main_window

SYNC_PROGRESS_STEPS = 1000

SYNC_WAIT_DIVISIONS = 100
SYNC_DELAY = 2
GET_TICKS = round(0.3 * SYNC_WAIT_DIVISIONS)
ADD_TICKS = round(0.05 * SYNC_WAIT_DIVISIONS)


def get_unsynced_edited():
    try:
        return set(serialise.load(paths.UNSYNCED_EDITED))
    except FileNotFoundError:
        return set()


def save_unsynced_edited(data):
    serialise.dump(list(data), paths.UNSYNCED_EDITED)


class MainWindow(QtWidgets.QMainWindow, Ui_main_window):
    def __init__(self, activities, *args, **kwargs):
        self.activities = activities
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        paths.ensure_all_present()

        self.settings = settings.load_settings()
        self.hide_unused_things()
        self.unsynced_edited_activities = get_unsynced_edited()

        # Create a global map widget to be used everywhere. This is
        # necessary because pyqtlet doesn't support multiple L.map
        # instances.
        self.map_widget = maps.MapWidget(self, self.settings)

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
            (self.action_match, "document-equal"),
            (self.action_analyse, "view-statistics"),
            (self.action_add_photos, "insert-image"),
            (self.action_general, "settings-configure"),
            (self.action_units, "measure"),
            (self.action_servers, "network-server"),
            (self.action_sync, "folder-sync"),
            (self.action_sync_settings, "folder-sync"),
            (self.export_menu, "document-send"),
            (self.action_quit, "application-exit"),
        ):
            widget.setIcon(QIcon.fromTheme(icon_name))

        self.main_tab_switch(0)

    def hide_unused_things(self):
        self.main_tabs.setTabVisible(2, bool(self.settings.servers))
        self.action_sync.setVisible(bool(self.settings.cookie))

    def edit_settings(self, tab):
        settings_window = activate.app.dialogs.settings.SettingsDialog()
        self.settings.copy_from(settings_window.exec(self.settings, tab))
        self.hide_unused_things()

    def edit_general_settings(self):
        self.edit_settings("General")

    def edit_unit_settings(self):
        self.edit_settings("Units")

    def edit_server_settings(self):
        self.edit_settings("Servers")

    def edit_sync_settings(self):
        self.edit_settings("Sync")

    def add_manual_activity(self):
        manual_window = activate.app.dialogs.activity.ManualActivityDialog()
        data = manual_window.exec({})
        if isinstance(data, dict):
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
                    data["Effort"],
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

    def sync(self):
        """Sync with another service."""
        dialog = QtWidgets.QProgressDialog("Syncing", "Cancel", 0, 0, self)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.forceShow()
        QtWidgets.qApp.processEvents()
        sync.sync_state.ensure_loaded()
        new_activities = sync.sync_state.sync(
            {"Strava": self.settings.cookie}, self.activities
        )
        new_activity_count = next(new_activities)
        if new_activity_count == 0:
            dialog.reset()
            return
        dialog.setMaximum(
            new_activity_count * SYNC_WAIT_DIVISIONS + GET_TICKS + ADD_TICKS
        )
        for progress in range(GET_TICKS, SYNC_WAIT_DIVISIONS):
            dialog.setValue(progress)
            time.sleep(SYNC_DELAY / SYNC_WAIT_DIVISIONS)
            if dialog.wasCanceled():
                dialog.reset()
                return
        done = False
        self.activity_list_table.setSortingEnabled(False)
        for index, new_activity in enumerate(new_activities):
            progress += GET_TICKS
            dialog.setValue(progress)
            dialog.setLabelText(f"Syncing {new_activity.name}")
            self.add_activity(new_activity)
            progress += ADD_TICKS
            dialog.setValue(progress)
            if index < new_activity_count - 1:
                for progress in range(progress, (index + 2) * SYNC_WAIT_DIVISIONS):
                    dialog.setValue(progress)
                    time.sleep(SYNC_DELAY / SYNC_WAIT_DIVISIONS)
                    if dialog.wasCanceled():
                        done = True
            if done:
                break
        else:
            dialog.setValue(progress + 1)
        sync.sync_state.write()

        self.activity_list_table.setCurrentCell(0, 0)
        self.activity_list_table.setSortingEnabled(True)
        self.main_tab_switch(self.main_tabs.currentIndex())

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
                **serialise.loads(
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

    def export_as_route(self):
        out_name = f"{self.activity.name}.gpx"
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export as Route", str(paths.HOME / out_name), "GPX file (*.gpx)"
        )[0]
        if not filename:
            return
        with open(filename, "w") as f:
            f.write(filetypes.gpx.to_route(self.activity))

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
                if item.activity_id == to_delete.activity_id:
                    self.activity_list_table.removeRow(row)
                    break
            self.activities.remove(to_delete.activity_id)
            return

        self.activity_list_table.setSortingEnabled(False)
        for row in range(len(self.activities)):
            if (
                self.activity_list_table.item(row, 0).activity_id
                == self.activity.activity_id
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

        self.unsynced_edited_activities.add(self.activity.activity_id)
        save_unsynced_edited(self.unsynced_edited_activities)

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
            activity_ = (
                self.activity
                if self.main_tabs.tabText(self.main_tabs.currentIndex()) == "Activities"
                else self.social_activity
            )
        except AttributeError:
            return
        self.activity_view.show_activity(activity_)
        self.activity_view.closed.connect(self.activity_view_closed)
        self.activity_view.create()
        self.activity_view.showMaximized()

    def match_activity(self):
        self.activity_list_table.setUpdatesEnabled(False)
        if self.action_match.text() == "Clear Match":
            self.action_match.setText("Find Matching")
            self.activity_list_table.filter({a.activity_id for a in self.activities})
        else:
            spinbox = QtWidgets.QSpinBox()
            spinbox.setMinimum(1)
            spinbox.setMaximum(500)
            spinbox.setSuffix(" m")
            tolerance = activate.app.dialogs.FormDialog(
                widgets.Form({"Tolerance": spinbox})
            ).exec({"Tolerance": 40})
            if tolerance:
                tolerance = tolerance["Tolerance"]
                self.activity_list_table.filter(
                    self.activities.get_matching(
                        self.activity,
                        tolerance=tolerance,
                        progress=lambda x: activate.app.dialogs.progress(
                            self, x, "Finding matching activities"
                        ),
                    )
                )
                self.action_match.setText("Clear Match")
        self.activity_list_table.setUpdatesEnabled(True)

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
        dialog = QtWidgets.QProgressDialog(
            "Syncing",
            "Cancel",
            0,
            len(self.settings.servers) * SYNC_PROGRESS_STEPS,
            self,
        )
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.forceShow()
        for i, server in enumerate(self.settings.servers):
            dialog.setLabelText(f"Getting activity list from {server.name}")
            dialog.setValue(SYNC_PROGRESS_STEPS * i)
            try:
                server_activities = activity_list.from_serial(
                    serialise.loads(server.get_data("get_activities")), None
                )
            except connect.requests.RequestException:
                continue
            own_ids = {a.activity_id for a in self.activities}
            dialog.setValue(round(SYNC_PROGRESS_STEPS * (i + 1 / 3)))
            dialog.setLabelText(f"Syncing activities with {server.name}")
            for j, activity_ in enumerate(server_activities):
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
                dialog.setValue(
                    round(
                        SYNC_PROGRESS_STEPS
                        * (i + (1 + (j + 1) / len(server_activities)) / 3)
                    )
                )
            dialog.setValue(round(SYNC_PROGRESS_STEPS * (i + 2 / 3)))
            own_ids |= self.unsynced_edited_activities
            if not own_ids:
                continue
            dialog.setLabelText(f"Uploading activities to {server.name}")
            for j, missing_id in enumerate(own_ids):
                try:
                    server.upload_activity(self.activities.get_activity(missing_id))
                    with suppress(KeyError):
                        self.unsynced_edited_activities.remove(missing_id)
                except connect.requests.RequestException:
                    break
                dialog.setValue(
                    round(SYNC_PROGRESS_STEPS * (i + (2 + (1 + j) / len(own_ids)) / 3))
                )
        save_unsynced_edited(self.unsynced_edited_activities)
        dialog.setValue(SYNC_PROGRESS_STEPS * len(self.settings.servers))

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
    app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    main_window = MainWindow(activity_list.from_disk(paths.DATA))

    main_window.showMaximized()
    sys.exit(app.exec())
