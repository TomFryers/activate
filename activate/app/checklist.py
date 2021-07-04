from __future__ import annotations

from typing import overload

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

Unchecked, PartiallyChecked, Checked = Qt.Unchecked, Qt.PartiallyChecked, Qt.Checked


class CheckList(QtWidgets.QListWidget):
    """A QListWidget with checkboxes on items."""

    def __init__(self, *args, **kwargs):
        self.do_not_recurse = False
        self.all_row = False
        super().__init__(*args, **kwargs)
        self.itemChanged.connect(self.item_changed)
        self.itemDoubleClicked.connect(self.item_double_clicked)

    @overload
    def __getitem__(self, index: int) -> QtWidgets.QListWidgetItem:
        ...

    @overload
    def __getitem__(self, index: slice) -> list[QtWidgets.QListWidgetItem]:
        ...

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self.item(i) for i in range(len(self))[index]]
        result = self.item(index)
        if result is None:
            raise IndexError(f"{self.__class__.__qualname__} index out of range")
        return result

    @property
    def row_names(self):
        return [row.text() for row in self]

    @row_names.setter
    def row_names(self, new_items):
        self.clear()
        self.addItems(new_items)
        for row in self:
            row.setCheckState(Unchecked)

    @property
    def states(self):
        return {row.text(): row.checkState() for row in self}

    @states.setter
    def states(self, new_states):
        for index, item in enumerate(self.row_names):
            if item in new_states:
                self.set_check_state(index, new_states[item])

    @property
    def num_states(self):
        return {
            row.text(): {Unchecked: 0, PartiallyChecked: 0.5, Checked: 1}[
                row.checkState()
            ]
            for row in self
        }

    @num_states.setter
    def num_states(self, new_states):
        for index, item in enumerate(self.row_names):
            if item in new_states:
                if new_states[item] == 0:
                    self.set_check_state(index, Unchecked)
                elif new_states[item] == 0.5:
                    self.set_check_state(index, PartiallyChecked)
                elif new_states[item] == 1:
                    self.set_check_state(index, Checked)

    def get_row(self, row):
        """Get a row from a string, index or row."""
        if isinstance(row, str):
            for real_row in self:
                if real_row.text() == row:
                    return real_row
            raise ValueError(f"{row} is not a row.")
        if isinstance(row, int):
            return self[row]
        return row

    def set_check_state(self, row, state):
        self.get_row(row).setCheckState(state)

    def check_state(self, row):
        return self.get_row(row).checkState()

    @property
    def checked_rows(self):
        return [r.text() for r in self if r.checkState() == Checked]

    def item_changed(self, item):
        if self.do_not_recurse or not self.all_row:
            return
        self.stop_updates()
        if self.is_all(item):
            for item_ in self[1:]:
                item_.setCheckState(item.checkState())
        else:
            states = {i.checkState() for i in self[1:]}
            self.set_all_state(
                next(iter(states)) if len(states) == 1 else PartiallyChecked
            )
        self.start_updates()

    def item_double_clicked(self, item):
        if self.is_all(item):
            self.set_all_state(Checked)
            return
        self.stop_updates()

        if self.all_row and len(self) > 2:
            self.set_all_state(PartiallyChecked)

        for item_ in self:
            if not self.is_all(item_):
                item_.setCheckState(Checked if item_ is item else Unchecked)
        self.start_updates()

    def check_all(self):
        for row in self:
            row.setCheckState(Checked)

    def add_all_row(self):
        self.insertItem(0, "All")
        self.all_row = True

    def is_all(self, item):
        """Check if a row is the 'All' row."""
        return self.all_row and self.row(item) == 0

    def set_all_state(self, state):
        if self.all_row:
            self.set_check_state(0, state)

    def stop_updates(self):
        self.do_not_recurse = True
        self.blockSignals(True)

    def start_updates(self):
        self.do_not_recurse = False
        self.blockSignals(False)
