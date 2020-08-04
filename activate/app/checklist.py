from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


def map_check_state(state) -> float:
    if state == Qt.Unchecked:
        return 0.0
    if state == Qt.PartiallyChecked:
        return 0.5
    if state == Qt.Checked:
        return 1.0
    raise ValueError(f"Invalid check state: {state!r}")


def unmap_check_state(state):
    if state == 0:
        return Qt.Unchecked
    if state == 0.5:
        return Qt.PartiallyChecked
    return Qt.Checked


class CheckList(QtWidgets.QListWidget):
    def __init__(self, *args, **kwargs):
        self.do_not_recurse = False
        self.all_row = False
        super().__init__(*args, **kwargs)
        self.itemChanged.connect(self.item_changed)
        self.itemDoubleClicked.connect(self.item_double_clicked)

    def __getitem__(self, index):
        result = self.item(index)
        if result is None:
            raise IndexError(f"{self.__class__.__name__} index out of range")
        return result

    @property
    def row_names(self):
        return [row.text() for row in self]

    @row_names.setter
    def row_names(self, new_items):
        self.clear()
        self.addItems(new_items)

    @property
    def states(self):
        return {row.text(): map_check_state(row.checkState()) for row in self}

    @states.setter
    def states(self, new_states):
        for index, item in enumerate(self.row_names):
            if item in new_states:
                self.set_check_state(index, new_states[item])

    def get_row(self, row):
        if isinstance(row, str):
            for real_row in self:
                if real_row.text() == row:
                    return real_row
        elif isinstance(row, int):
            return self[row]
        return row

    def set_check_state(self, row, state):
        row = self.get_row(row)
        if not isinstance(state, Qt.CheckState):
            state = unmap_check_state(state)
        row.setCheckState(state)

    def check_state(self, row):
        return map_check_state(self.get_row(row).checkState())

    @property
    def checked_rows(self):
        return [r.text() for r in self if r.checkState() == Qt.Checked]

    def item_changed(self, item):
        if self.do_not_recurse:
            return
        self.do_not_recurse = True
        if (
            self.all_row
            and item.text() == "All"
            and item.checkState() != Qt.PartiallyChecked
        ):
            for i in range(1, len(self)):
                self.set_check_state(i, item.checkState())
        else:
            states = set(
                self.check_state(i) for i in range(1 if self.all_row else 0, len(self))
            )
            if self.all_row:
                if len(states) == 1:
                    new_state = next(iter(states))
                else:
                    new_state = 0.5
                self.set_check_state(0, new_state)
        self.do_not_recurse = False

    def item_double_clicked(self, item):
        if self.all_row and item.text() == "All":
            self.set_check_state(0, 1.0)
            return
        self.do_not_recurse = True
        if self.all_row and len(self) > 2:
            self.set_check_state(0, 0.5)

        for item_ in self:
            if not (self.all_row and item_.text() == "All"):
                item_.setCheckState(Qt.Checked if item_ is item else Qt.Unchecked)
        self.do_not_recurse = False

    def check_all(self):
        for row in self:
            row.setCheckState(Qt.Checked)

    def add_all_row(self):
        self.insertItem(0, "All")
        self.all_row = True
