import collections
from datetime import timedelta

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from activate import activity_types, times
from activate import units as units_
from activate.app import checklist

UNIVERSAL_FLAGS = ("Commute", "Indoor")
TYPE_FLAGS = collections.defaultdict(tuple)
TYPE_FLAGS.update(activity_types.FLAGS)

EFFORT_LEVELS = (
    "None",
    "Very easy",
    "Easy",
    "Quite easy",
    "Moderate",
    "Quite hard",
    "Hard",
    "Very hard",
    "Extreme",
    "Maximum",
)


class ActivityFlagEdit(checklist.CheckList):
    def change_options(self, activity_type):
        self.row_names = TYPE_FLAGS[activity_type] + UNIVERSAL_FLAGS


class DurationEdit(QtWidgets.QFormLayout):
    """A widget to allow editing an hours minute seconds duration."""

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
        return timedelta(
            hours=self.hours_widget.value(),
            minutes=self.minutes_widget.value(),
            seconds=self.seconds_widget.value(),
        )

    def set_value(self, new: timedelta):
        hours, minutes, seconds = times.hours_minutes_seconds(new)
        self.hours_widget.setValue(hours)
        self.minutes_widget.setValue(minutes)
        self.seconds_widget.setValue(seconds)


class EffortEdit(QtWidgets.QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slider = QtWidgets.QSlider(Qt.Horizontal, self.parent())
        self.slider.setMaximum(9)
        self.slider.valueChanged.connect(self.set_label)
        self.slider.sliderPressed.connect(self.set_label)
        self.addWidget(self.slider)
        self.label = QtWidgets.QLabel("Unspecified")
        self.addWidget(self.label)

    def set_label(self):
        self.label.setText(EFFORT_LEVELS[self.slider.value()])

    def value(self):
        if self.label.text() == "Unspecified":
            return None
        return self.slider.value()

    def set_value(self, value):
        if value is None:
            self.slider.setValue(0)
            self.label.setText("Unspecified")
        else:
            self.slider.setValue(value)


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
    checklist.CheckList: lambda w: w.num_states,
    DurationEdit: lambda w: w.value(),
    EffortEdit: lambda w: w.value(),
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
    checklist.CheckList: lambda w, v: setattr(w, "num_states", v),
    DurationEdit: lambda w, v: w.set_value(v),
    EffortEdit: lambda w, v: w.set_value(v),
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


class CustomUnits(QtWidgets.QFormLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.combo_boxes = {}
        self.labels = list(units_.ALL.keys())
        for unit, options in units_.ALL.items():
            if len(options) <= 1:
                continue
            combo_box = QtWidgets.QComboBox()
            combo_box.addItem("Default")
            for option in options:
                combo_box.addItem(option.name.capitalize())
            self.addRow(unit.replace("_", " ").title(), combo_box)
            self.combo_boxes[unit] = combo_box

    def units_dict(self):
        result = {}
        for unit in self.combo_boxes:
            value = self.combo_boxes[unit].currentText()
            if value == "Default":
                continue
            result[unit] = value.casefold()
        return result

    def set_units(self, units):
        for unit, value in units.items():
            self.combo_boxes[unit].setCurrentIndex(
                self.combo_boxes[unit].findText(value.capitalize())
            )
