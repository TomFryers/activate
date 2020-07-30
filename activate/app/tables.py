"""Classes inheriting from QTableWidgets or QTableWidgetItems."""
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from activate.core import number_formats, times, units


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
        widget.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
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
        for column, (value, format, align) in enumerate(
            zip(values, formats, alignments)
        ):
            self.set_item(position, column, value, format, align)

    @property
    def headings(self):
        return [self.get_heading(i) for i in range(self.columnCount())]

    def get_heading(self, index) -> str:
        return self.horizontalHeaderItem(index).text()


class ValueColumnTable(QtWidgets.QTableWidget):
    def lock_column_count(self):
        """
        Disable the setColumnCount method.

        Use the unlock_column_count method to re-enable it. This method
        is useful because PyQt5.uic calls setColumnCount on objects
        after they are created.
        """

        self.oldSetColumnCount = self.setColumnCount
        self.setColumnCount = lambda x: None

    def unlock_column_count(self):
        self.setColumnCount = self.oldSetColumnCount

    def resize_to_contents(self, vertical=False):
        if vertical:
            header = self.verticalHeader()
        else:
            header = self.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def define_columns(self, names, format_functions=None, alignments=None):
        self.setColumnCount(len(names))
        self.setHorizontalHeaderLabels(names)
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


class SplitTable(ValueColumnTable):
    headings = ["Number", "Time", "Split", "Speed", "Net Climb", "Ascent"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.define_columns(
            self.headings,
            [number_formats.split_format(h) for h in self.headings],
            alignments=[Qt.AlignRight | Qt.AlignVCenter for _ in self.headings],
        )

        self.resize_to_contents()
        self.lock_column_count()

    def update_data(self, data):
        self.setRowCount(len(data))
        for y, row in enumerate(data):
            row_data = [y + 1] + row
            self.set_row(row_data, y)


class ActivityListTable(ValueColumnTable):
    headings = ["Name", "Type", "Start Time", "Distance"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.insertRow(0)
        self.define_columns(
            self.headings, [number_formats.list_format(h) for h in self.headings],
        )
        self.resize_to_contents()
        self.resize_to_contents(vertical=True)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.lock_column_count()

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
        self.insertRow(position)
        self.set_id_row(activity_id, values, position)

    def default_sort(self):
        self.sortItems(2, Qt.DescendingOrder)


class CurveTable(ValueColumnTable):
    headings = ["Distance", "Time", "Speed"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.define_columns(
            self.headings, [lambda x: x, times.to_string, lambda x: str(round(x, 1)),],
        )
        self.lock_column_count()
        self.resize_to_contents()

    def update_data(self, good_distance_names, table):
        self.setRowCount(len(table))
        for index, row in enumerate(table):
            self.set_row(good_distance_names[index : index + 1] + list(row[1:]), index)


class InfoTable(Table):
    """
    The table widget on the right.

    This is used for distance, climb, duration etc.
    """

    def update_data(self, info: dict):
        self.setRowCount(len(info))
        for row, (field, value) in enumerate(info.items()):
            self.set_item(row, 0, field)
            self.set_item(
                row,
                1,
                value,
                number_formats.info_format(field),
                align=Qt.AlignRight | Qt.AlignVCenter,
            )
            self.set_item(
                row,
                2,
                self.unit_system.units[value.dimension].symbol,
                align=Qt.AlignLeft | Qt.AlignVCenter,
            )
