"""Classes inheriting from QTableWidgets or QTableWidgetItems."""
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from activate.core import units


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

    def headings(self):
        return [self.get_heading(i) for i in range(self.columnCount())]

    def get_heading(self, index) -> str:
        return self.horizontalHeaderItem(index).text()


class ActivityListTable(Table):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def current_activity_id(self):
        return self.selectedItems()[0].activity_id

    def set_row(self, activity_id, values, position, formats=None, alignments=None):
        super().set_row(values, position, formats, alignments)
        self.item(position, 0).activity_id = activity_id
