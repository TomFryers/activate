import datetime

import PyQt5
from PyQt5 import QtWidgets

from activate import activity_types
from activate.app import paths
from activate.app.dialogs import FormDialog
from activate.app.widgets import ActivityFlagEdit, DurationEdit, EffortEdit, Form

DELETE_ACTIVITY = 222  # 0xDE[lete]


class ManualActivityDialog(FormDialog):
    def __init__(self, *args, **kwargs):
        layout = {
            "Name": QtWidgets.QLineEdit(),
            "Type": QtWidgets.QComboBox(),
            "Distance": QtWidgets.QDoubleSpinBox(),
            "Start Time": QtWidgets.QDateTimeEdit(),
            "Duration": DurationEdit(),
            "Ascent": QtWidgets.QDoubleSpinBox(),
            "Flags": ActivityFlagEdit(),
            "Effort": EffortEdit(),
            "Description": QtWidgets.QPlainTextEdit(),
        }
        layout["Type"].currentTextChanged.connect(layout["Flags"].change_options)
        layout["Type"].addItems(activity_types.TYPES)
        layout["Distance"].setRange(0, 100000)
        layout["Ascent"].setRange(0, 100000)
        super().__init__(Form(layout), *args, **kwargs)
        self.setWindowTitle("Manual Activity")

    def accept(self):
        if self.form.fields["Duration"].value() > datetime.timedelta(0):
            super().accept()


class EditActivityDialog(FormDialog):
    def __init__(self, *args, **kwargs):
        layout = {
            "Name": QtWidgets.QLineEdit(),
            "Type": QtWidgets.QComboBox(),
            "Flags": ActivityFlagEdit(),
            "Effort": EffortEdit(),
            "Description": QtWidgets.QPlainTextEdit(),
        }
        layout["Type"].currentTextChanged.connect(layout["Flags"].change_options)
        layout["Type"].addItems(activity_types.TYPES)
        super().__init__(Form(layout), *args, **kwargs)
        self.setWindowTitle("Edit Activity")
        self.add_delete_button()

    def add_delete_button(self):
        self.delete_button = QtWidgets.QPushButton("Delete Activity")
        self.delete_button.setIcon(PyQt5.QtGui.QIcon.fromTheme("edit-delete"))
        self.delete_button.clicked.connect(self.handle_delete_button)
        self.main_layout.insertWidget(1, self.delete_button)

    def apply_to_activity(self, data):
        """Apply the settings to an self.activity."""
        self.activity.name = data["Name"]
        self.activity.sport = data["Type"]
        self.activity.description = data["Description"]
        self.activity.flags = data["Flags"]
        self.activity.effort_level = data["Effort"]
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
        result = super().exec(
            {
                "Name": self.activity.name,
                "Type": self.activity.sport,
                "Flags": self.activity.flags,
                "Effort": self.activity.effort_level,
                "Description": self.activity.description,
            }
        )
        if isinstance(result, dict):
            self.apply_to_activity(result)
        return result


class EditManualActivityDialog(EditActivityDialog, ManualActivityDialog):
    def __init__(self, *args, **kwargs):
        ManualActivityDialog.__init__(self, *args, **kwargs)
        self.setWindowTitle("Edit Activity")
        self.add_delete_button()

    def apply_to_activity(self, data):
        super().apply_to_activity(data)
        self.activity.track.length = data["Distance"]
        self.activity.track.start_time = data["Start Time"]
        self.activity.track.elapsed_time = data["Duration"]
        self.activity.track.ascent = data["Ascent"]

    def exec(self, activity):
        self.activity = activity

        result = ManualActivityDialog.exec(
            self,
            {
                "Name": self.activity.name,
                "Type": self.activity.sport,
                "Distance": self.activity.track.length / 1000,
                "Start Time": self.activity.track.start_time,
                "Duration": self.activity.track.elapsed_time,
                "Ascent": self.activity.track.ascent,
                "Flags": self.activity.flags,
                "Effort": self.activity.effort_level,
                "Description": self.activity.description,
            },
        )
        if isinstance(result, dict):
            self.apply_to_activity(result)
        return result
