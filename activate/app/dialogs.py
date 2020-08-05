import collections
import datetime

import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from activate.app import checklist, paths, settings
from activate.core import activity_types, times

UNIVERSAL_FLAGS = ("Commute", "Indoor")
TYPE_FLAGS = collections.defaultdict(tuple)
TYPE_FLAGS.update(activity_types.FLAGS)
DELETE_ACTIVITY = 222  # 0xDE[lete]


class DurationEdit(QtWidgets.QFormLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hours_widget = QtWidgets.QSpinBox()
        self.addRow("Hours", self.hours_widget)
        self.minutes_widget = QtWidgets.QSpinBox()
        self.minutes_widget.setRange(0, 59)
        self.addRow("Minutes", self.minutes_widget)
        self.seconds_widget = QtWidgets.QDoubleSpinBox()
        self.seconds_widget.setRange(0, 59.99)
        self.addRow("Seconds", self.seconds_widget)

    def value(self):
        return datetime.timedelta(
            hours=self.hours_widget.value(),
            minutes=self.minutes_widget.value(),
            seconds=self.seconds_widget.value(),
        )

    def set_value(self, new: datetime.timedelta):
        hours, minutes, seconds = times.hours_minutes_seconds(new)
        self.hours_widget.setValue(hours)
        self.minutes_widget.setValue(minutes)
        self.seconds_widget.setValue(seconds)


class ActivityFlagEdit(checklist.CheckList):
    def change_options(self, activity_type):
        self.row_names = TYPE_FLAGS[activity_type] + UNIVERSAL_FLAGS


WIDGET_VALUES = {
    QtWidgets.QLineEdit: lambda w: w.text(),
    QtWidgets.QPlainTextEdit: lambda w: w.toPlainText(),
    QtWidgets.QTextEdit: lambda w: w.text(),
    QtWidgets.QSpinBox: lambda w: w.value(),
    QtWidgets.QDoubleSpinBox: lambda w: w.value(),
    QtWidgets.QComboBox: lambda w: w.currentText(),
    QtWidgets.QTimeEdit: lambda w: w.time().toPyTime(),
    QtWidgets.QDateTimeEdit: lambda w: w.dateTime().toPyDateTime(),
    QtWidgets.QDateEdit: lambda w: w.date().toPyDate(),
    QtWidgets.QAbstractSlider: lambda w: w.value(),
    QtWidgets.QKeySequenceEdit: lambda w: w.keySequence(),
    checklist.CheckList: lambda w: w.states,
    DurationEdit: lambda w: w.value(),
}

WIDGET_SETTERS = {
    QtWidgets.QLineEdit: lambda w, v: w.setText(v),
    QtWidgets.QPlainTextEdit: lambda w, v: w.setPlainText(v),
    QtWidgets.QTextEdit: lambda w, v: w.setText(v),
    QtWidgets.QSpinBox: lambda w, v: w.setValue(v),
    QtWidgets.QDoubleSpinBox: lambda w, v: w.setValue(v),
    QtWidgets.QComboBox: lambda w, v: w.setCurrentText(v),
    QtWidgets.QTimeEdit: lambda w, v: w.setTime(v),
    QtWidgets.QDateTimeEdit: lambda w, v: w.setDateTime(v),
    QtWidgets.QDateEdit: lambda w, v: w.setDate(v),
    QtWidgets.QAbstractSlider: lambda w, v: w.setValue(v),
    QtWidgets.QKeySequenceEdit: lambda w, v: w.setKeySequence(v),
    checklist.CheckList: lambda w, v: setattr(w, "state", v),
    DurationEdit: lambda w, v: w.set_value(v),
}


def get_value(widget):
    for widget_type, function in WIDGET_VALUES.items():
        if isinstance(widget, widget_type):
            return function(widget)


def set_value(widget, value):
    for widget_type, function in WIDGET_SETTERS.items():
        if isinstance(widget, widget_type):
            return function(widget, value)


class Form(QtWidgets.QFormLayout):
    def __init__(self, fields, *args, **kwargs):
        self.fields = fields
        super().__init__(*args, **kwargs)
        for (name, entry) in self.fields.items():
            self.addRow(name, entry)

    def values(self):
        return {
            name: get_value(
                self.itemAt(index, self.FieldRole).widget()
                or self.itemAt(index, self.FieldRole).layout()
            )
            for index, name in enumerate(self.fields.keys())
        }

    def set_values(self, values):
        for index, name in enumerate(self.fields.keys()):
            if name in values:
                set_value(
                    self.itemAt(index, self.FieldRole).widget()
                    or self.itemAt(index, self.FieldRole).layout(),
                    values[name],
                )


class FormDialog(QtWidgets.QDialog):
    def __init__(self, form, *args, **kwargs):
        self.form = form
        super().__init__(*args, **kwargs)
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.main_layout.addLayout(self.form)

        self.buttons = QtWidgets.QDialogButtonBox(self)
        self.buttons.setStandardButtons(self.buttons.Cancel | self.buttons.Ok)

        self.main_layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def exec(self, initial_values: dict):
        self.form.set_values(initial_values)
        result = super().exec()
        if not result:
            return None
        elif result == 1:
            return self.form.values()
        return result


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
            "Description": QtWidgets.QPlainTextEdit(),
        }
        layout["Type"].currentTextChanged.connect(layout["Flags"].change_options)
        layout["Type"].addItems(activity_types.TYPES)
        super().__init__(*args, form=Form(layout), **kwargs)
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
            "Description": QtWidgets.QPlainTextEdit(),
        }
        layout["Type"].currentTextChanged.connect(layout["Flags"].change_options)
        layout["Type"].addItems(activity_types.TYPES)
        super().__init__(*args, form=Form(layout), **kwargs)
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
                "Description": self.activity.description,
            }
        )
        if result and result != DELETE_ACTIVITY:
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
                "Description": self.activity.description,
            },
        )
        if result and result != DELETE_ACTIVITY:
            self.apply_to_activity(result)
        return result


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PyQt5.uic.loadUi("resources/ui/settings.ui", self)

    def load_from_settings(self, current_settings: settings.Settings):
        """Load a Settings object to the UI widgets."""
        self.unit_system.setCurrentText(current_settings.unit_system)

    def get_settings(self) -> settings.Settings:
        """Get a Settings object from the UI widgets."""
        return settings.Settings(unit_system=self.unit_system.currentText())

    def exec(self, current_settings, page):
        self.settings_tabs.setCurrentIndex(("Units",).index(page))
        result = super().exec()
        if not result:
            return current_settings
        new_settings = self.get_settings()
        new_settings.save()
        return new_settings
