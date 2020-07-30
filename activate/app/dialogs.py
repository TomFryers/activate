import collections

import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from activate.app import paths, settings
from activate.core import activity_types

UNIVERSAL_FLAGS = ("Commute", "Indoor")
TYPE_FLAGS = collections.defaultdict(tuple)
TYPE_FLAGS.update(activity_types.FLAGS)
DELETE_ACTIVITY = 222  # 0xDE[lete]


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PyQt5.uic.loadUi("resources/ui/settings.ui", self)

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
        PyQt5.uic.loadUi("resources/ui/edit_activity.ui", self)
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

        self.activity.save(paths.ACTIVITIES)

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
