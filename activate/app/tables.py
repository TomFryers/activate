"""Classes inheriting from QTableWidgets or QTableWidgetItems."""
import dataclasses

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from activate import number_formats, times, units
from activate.app import connect


def aligned(horizontal="c", vertical="c"):
    """
    Get a Qt Alignment from a string.

    The first argument gives the horizontal alignment:
    Left, Centre, Right or Justified.
    The second argument gives the vertical alignment:
    Bottom, Centre, Top or bAseline.
    """
    return {
        "l": Qt.AlignLeft,
        "c": Qt.AlignHCenter,
        "r": Qt.AlignRight,
        "v": Qt.AlignJustify,
    }[horizontal.casefold()] | {
        "b": Qt.AlignBottom,
        "c": Qt.AlignVCenter,
        "t": Qt.AlignTop,
        "a": Qt.AlignBaseline,
    }[
        vertical.casefold()
    ]


def iterablise(obj):
    """If obj is not already iterable, form an endless iterator of it."""
    try:
        iter(obj)
        return obj
    except TypeError:
        # Infinite iterator
        return iter(lambda: obj, object())


def create_table_item(
    item, format_function=None, unit_system=None, align=None
) -> QtWidgets.QTableWidgetItem:
    """
    Create a table item that can be a FormattableNumber.

    If item is a tuple, will return a table item that looks like item[1]
    but sorts with item[0]. Otherwise just returns a normal table item.
    """
    if isinstance(item, units.DimensionValue):
        item = item.encode(unit_system)

    if format_function is not None:
        widget = FormattableNumber(item, format_function(item))
        widget.setTextAlignment(aligned("r"))
    # Format as string
    else:
        widget = QtWidgets.QTableWidgetItem(str(item))
    if align is not None:
        widget.setTextAlignment(align)
    return widget


def good_minus(string):
    """Replace an initial hyphen-minuses with a real minus sign."""
    if string and string[0] == "-":
        return "\u2212" + string[1:]
    return string


class FormattableNumber(QtWidgets.QTableWidgetItem):
    """A sortable, formatted number to place in a table."""

    def __init__(self, number, text):
        super().__init__(good_minus(text))
        self.number = number

    def __lt__(self, other):
        return self.number < other.number


class Table(QtWidgets.QTableWidget):
    unit_system = None

    def resize_to_contents(self, direction="h"):
        """
        Set a header to auto-resize its items.

        This also stops the user resizing them, which is good because
        usually resizing these things is not particularly useful.
        """
        if direction == "h":
            header = self.horizontalHeader()
        elif direction == "v":
            header = self.verticalHeader()
        else:
            raise ValueError(f"Invalid direction: {direction}. (Must be 'h' or 'v')")

        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def set_item(self, row, column, value, format_function=None, align=None):
        self.setItem(
            row,
            column,
            create_table_item(value, format_function, self.unit_system, align=align),
        )

    def set_row(self, values, position, formats=None, alignments=None):
        alignments = iterablise(alignments)
        formats = iterablise(formats)
        for column, (value, format_, align) in enumerate(
            zip(values, formats, alignments)
        ):
            self.set_item(position, column, value, format_, align)

    def get_row_text(self, index) -> list:
        result = []
        for column in range(self.columnCount()):
            item = self.item(index, column)
            result.append(None if item is None else item.text())
        return result

    @property
    def headings(self):
        return [self.get_heading(i) for i in range(self.columnCount())]

    def get_heading(self, index) -> str:
        return self.horizontalHeaderItem(index).text()


class ValueColumnTable(QtWidgets.QTableWidget):
    def set_units(self, unit_system):
        self.unit_system = unit_system

    def resize_to_contents(self, vertical=False):
        if vertical:
            header = self.verticalHeader()
        else:
            header = self.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def define_columns(self, names, dimensions, format_functions=None, alignments=None):
        self.setColumnCount(len(names))
        self.setHorizontalHeaderLabels(
            [
                self.unit_system.format_name_unit(
                    name, self.unit_system.units[dimension].symbol
                )
                for name, dimension in zip(names, dimensions)
            ]
        )
        if format_functions is None:
            self.format_functions = [None for _ in names]
        else:
            self.format_functions = format_functions
        if alignments is None:
            self.alignments = [None for _ in names]
        else:
            self.alignments = alignments

    def set_item(self, row, column, value):
        self.setItem(
            row,
            column,
            create_table_item(
                value,
                self.format_functions[column],
                self.unit_system,
                self.alignments[column],
            ),
        )

    def set_row(self, values, position):
        for column, value in enumerate(values):
            self.set_item(position, column, value)

    def __len__(self):
        return self.rowCount()


class SplitTable(ValueColumnTable):
    headings = ["Number", "Time", "Split", "Speed", "Net Climb", "Ascent"]
    dimensions = [None, "time", "time", "speed", "altitude", "altitude"]

    def set_units(self, *args, **kwargs):
        super().set_units(*args, **kwargs)
        self.define_columns(
            self.headings,
            self.dimensions,
            [number_formats.split_format(h) for h in self.headings],
            alignments=[aligned("r") for _ in self.headings],
        )

        self.resize_to_contents()

    def update_data(self, data):
        self.setRowCount(len(data))
        for y, row in enumerate(data):
            row_data = [y + 1] + row
            self.set_row(row_data, y)


class ActivityListTable(ValueColumnTable):
    headings = ["Name", "Type", "Start Time", "Distance"]
    dimensions = [None, None, None, "distance"]
    right_clicked = QtCore.pyqtSignal(QtCore.QEvent)

    def set_units(self, *args, **kwargs):
        super().set_units(*args, **kwargs)
        self.define_columns(
            self.headings,
            self.dimensions,
            [number_formats.list_format(h) for h in self.headings],
        )
        self.resize_to_contents()
        self.resize_to_contents(vertical=True)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

    @property
    def current_activity_id(self):
        return self.selectedItems()[0].activity_id

    def set_id_row(self, activity_id, values, position):
        """
        Set the items in the given activity list row to specific values.

        Assigns activity_id to the item in column zero in the new_row.
        """
        self.set_row(values, position)
        self.item(position, 0).activity_id = activity_id

    def add_id_row(self, activity_id, values, position):
        sorting_was_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
        self.insertRow(position)
        self.set_id_row(activity_id, values, position)
        if sorting_was_enabled:
            self.setSortingEnabled(True)

    def default_sort(self):
        self.setSortingEnabled(True)
        self.sortItems(self.headings.index("Start Time"), Qt.DescendingOrder)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.right_clicked.emit(event)
        else:
            super().mouseReleaseEvent(event)

    def select(self, activity_id):
        for row in range(len(self)):
            if self.item(row, 0).activity_id == activity_id:
                self.selectRow(row)
                return

    def filter(self, ids):
        for row in range(len(self)):
            self.setRowHidden(row, self.item(row, 0).activity_id not in ids)


class SocialActivityList(ActivityListTable):
    headings = ["Server", "User", "Name", "Type", "Start Time", "Distance"]
    dimensions = [None, None, None, None, None, "distance"]

    def filter_by_server(self, allowed):
        for row in range(len(self)):
            servers = self.item(row, 0).text().split("\n")
            usernames = self.item(row, 1).text().split("\n")
            self.setRowHidden(
                row, not any(x in allowed for x in zip(servers, usernames))
            )


class CurveTable(ValueColumnTable):
    headings = ["Distance", "Time", "Speed"]
    dimensions = [None, "time", "speed"]

    def set_units(self, *args, **kwargs):
        super().set_units(*args, **kwargs)
        self.define_columns(
            self.headings,
            self.dimensions,
            [lambda x: x, times.to_string, lambda x: str(round(x, 1))],
        )

    def update_data(self, good_distance_names, table):
        self.setRowCount(len(table))
        for index, row in enumerate(table):
            self.set_row(good_distance_names[index : index + 1] + list(row[1:]), index)


class RecordsTable(CurveTable):
    headings = CurveTable.headings + ["Activity"]
    dimensions = CurveTable.dimensions + [None]
    # An int results in an overflow issue
    gone_to = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.itemDoubleClicked.connect(self.go_to)

    def set_units(self, *args, **kwargs):
        super().set_units(*args, **kwargs)
        self.define_columns(
            self.headings,
            self.dimensions,
            [lambda x: x, times.to_string, lambda x: str(round(x, 1)), lambda x: x],
        )
        self.resize_to_contents()

    def update_data(self, good_distance_names, table, activity_ids):
        super().update_data(good_distance_names, table)
        for row, activity_id in enumerate(activity_ids):
            self.item(row, self.headings.index("Activity")).activity_id = activity_id

    def go_to(self, item):
        if self.headings[item.column()] == "Activity":
            self.gone_to.emit(item.activity_id)


class InfoTable(Table):
    """
    The table widget on the right.

    This is used for distance, climb, duration etc.
    """

    def set_units(self, unit_system):
        self.unit_system = unit_system

    def update_data(self, info: dict):
        self.setRowCount(len(info))
        for row, (field, value) in enumerate(info.items()):
            self.set_item(row, 0, field)
            self.set_item(
                row, 1, value, number_formats.info_format(field), align=aligned("r")
            )
            self.set_item(
                row,
                2,
                self.unit_system.units[value.dimension].symbol,
                align=aligned("l"),
            )


class ServersTable(Table):
    headings = ["Address", "Name", "Username", "Password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up right click delete menu
        self.menu = QtWidgets.QMenu(self)
        self.action_delete = QtWidgets.QAction("Delete")
        self.action_delete.setIcon(QIcon.fromTheme("edit-delete"))
        self.menu.addAction(self.action_delete)

    def set_columns(self):
        self.setColumnCount(len(self.headings))
        self.setHorizontalHeaderLabels(self.headings)

    def set_server(self, row, server):
        self.set_row(["" if x is None else x for x in dataclasses.astuple(server)], row)

    def set_servers(self, servers):
        self.setRowCount(len(servers))
        self.set_columns()
        for row, server in enumerate(servers):
            self.set_server(row, server)

    def get_servers(self):
        return [connect.Server(*self.get_row_text(r)) for r in range(self.rowCount())]

    def add_row(self):
        self.setRowCount(self.rowCount() + 1)
        self.set_columns()

    def contextMenuEvent(self, event):
        """Open a context menu to remove a server."""
        if self.menu.exec(event.globalPos()):
            self.removeRow(self.row(self.itemAt(event.pos())))
