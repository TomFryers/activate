import PyQt5
import PyQt5.uic
import pyqtlet
from PyQt5 import QtCore, QtWidgets

import charts
import load_activity
import number_formats
import settings
import times
import units

ACTIVITY_TYPES = ("Run", "Ride", "Swim", "Walk", "Ski", "Row", "Other")

UNIVERSAL_FLAGS = ("Commute", "Indoor")
TYPE_FLAGS = {
    "Run": ("Race", "Long Run", "Workout", "Treadmill"),
    "Ride": ("Race", "Workout"),
}


def default_map_location(route):
    """Calculate the mean position for centering the map."""
    return [
        (min(p[component] for p in route) + max(p[component] for p in route)) / 2
        for component in range(2)
    ]


def create_table_item(item, align=None) -> QtWidgets.QTableWidgetItem:
    """
    Create a table item that can be a FormattableNumber.

    If item is a tuple, will return a table item that looks like item[1]
    but sorts with item[0]. Otherwise just returns a normal table item.
    """
    if isinstance(item, tuple):
        widget = FormattableNumber(*item)
        widget.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
    # Format as string
    else:
        widget = QtWidgets.QTableWidgetItem(item)
    if align is not None:
        widget.setTextAlignment(align)
    return widget


def good_minus(string):
    """Replace hyphen-minuses with real minus signs."""
    return string.replace("-", "\u2212")


class FormattableNumber(QtWidgets.QTableWidgetItem):
    """A sortable, formatted number to place in a table."""

    def __init__(self, number, text):
        super().__init__(good_minus(text))
        self.number = number

    def __lt__(self, other):
        return self.number < other.number


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PyQt5.uic.loadUi("settings.ui", self)

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
        PyQt5.uic.loadUi("edit_activity.ui", self)
        self.type_edit.addItems(ACTIVITY_TYPES)

    def update_flags(self):
        """Generate the flags in the list based on the activity."""
        if "activity" not in vars(self):
            return
        self.flags = TYPE_FLAGS[self.type_edit.currentText()] + UNIVERSAL_FLAGS
        self.flag_list.clear()
        self.flag_list.addItems(self.flags)
        for i, flag in enumerate(self.flags):
            self.flag_list.item(i).setCheckState(
                QtCore.Qt.Checked
                if flag in self.activity.flags and self.activity.flags[flag]
                else QtCore.Qt.Unchecked
            )

    def load_from_activity(self):
        """Load an self.activity's data to the UI."""
        self.name_edit.setText(self.activity.name)
        self.type_edit.setCurrentText(self.activity.sport)
        self.update_flags()

    def apply_to_activity(self):
        """Apply the settings to an self.activity."""
        self.activity.name = self.name_edit.text()
        self.activity.sport = self.type_edit.currentText()
        for i, flag in enumerate(self.flags):
            self.activity.flags[flag] = (
                self.flag_list.item(i).checkState() == QtCore.Qt.Checked
            )

        self.activity.save()

    def exec(self, activity):
        self.activity = activity
        self.load_from_activity()
        result = super().exec()
        if result:
            self.apply_to_activity()
        return result


def resize_to_contents(header):
    """
    Set a header to auto-resize its items.

    This also stops the user resizing them, which is good because usually
    resizing these things is not particularly useful.
    """
    header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        PyQt5.uic.loadUi("main.ui", self)
        self.updated = set()

        self.settings = settings.load_settings()

        # Set up map
        self.map_widget = pyqtlet.MapWidget()
        self.map_widget.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.map = pyqtlet.L.map(self.map_widget, {"attributionControl": False})
        self.map_container.addWidget(self.map_widget)
        self.map.setView([51, -1], 14)
        pyqtlet.L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png").addTo(self.map)

        # Set activity list heading resize modes
        header = self.activity_list_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)

        # Disable resizing in activity list
        resize_to_contents(self.activity_list_table.verticalHeader())
        resize_to_contents(self.split_table.horizontalHeader())

        # Set up charts
        self.charts = {}
        self.charts["ele"] = charts.LineChart(
            self.altitude_graph, self.unit_system, "Altitude", area=True
        )
        self.charts["speed"] = charts.LineChart(
            self.speed_graph, self.unit_system, "Speed", area=False
        )
        self.zones = list(range(0, 20)) + [float("inf")]
        self.zones = [self.unit_system.decode(x, "speed") for x in self.zones]
        self.charts["zones"] = charts.Histogram(
            self.zones, self.zones_graph, self.unit_system
        )

        self.action_import.setIcon(PyQt5.QtGui.QIcon.fromTheme("document-open"))
        self.action_quit.setIcon(PyQt5.QtGui.QIcon.fromTheme("application-exit"))

    def edit_unit_settings(self):
        settings_window = SettingsDialog()
        self.settings = settings_window.exec(self.settings, "Units")

    def edit_activity_data(self):
        edit_activity_dialog = EditActivityDialog()
        if not edit_activity_dialog.exec(self.activity):
            return
        self.activity_list_table.setSortingEnabled(False)
        for row in range(len(self.activities)):
            if (
                self.activities.from_link(id(self.activity_list_table.item(row, 0)))
                == self.activity
            ):
                link = self.assign_activity_items(
                    self.activity.create_unloaded().list_row, row
                )
        self.activities.update(
            self.activity.activity_id, link,
        )
        self.update_activity(row)
        self.activity_list_table.setSortingEnabled(True)

    def show_on_map(self, route: list):
        """Display a list of points on the map."""
        self.map.setView(default_map_location(route))
        try:
            self.map.removeLayer(self.route_line)
            self.map.removeLayer(self.start_icon)
            self.map.removeLayer(self.finish_icon)
        except AttributeError:
            pass
        self.route_line = pyqtlet.L.polyline(
            route, {"smoothFactor": 0, "color": "#802090"}
        )
        self.start_icon = pyqtlet.L.circleMarker(
            route[0], {"radius": 8, "color": "#10b020"}
        )
        self.finish_icon = pyqtlet.L.circleMarker(
            route[-1], {"radius": 8, "color": "#e00000"}
        )
        self.start_icon.addTo(self.map)
        self.finish_icon.addTo(self.map)
        self.route_line.addTo(self.map)

    def add_info(self, info: dict):
        """
        Add data to the table widget on the right.

        This is used for distance, climb, duration etc.
        """
        self.info_table.setRowCount(len(info))
        for i, (k, v) in enumerate(info.items()):
            self.info_table.setItem(i, 0, create_table_item(k))
            if isinstance(v, tuple):
                value, unit = self.unit_system.format(*v)
            else:
                value = v
                unit = None
            self.info_table.setItem(
                i,
                1,
                create_table_item(
                    (value, number_formats.info_format(value, k)),
                    align=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                ),
            ),
            self.info_table.setItem(
                i,
                2,
                create_table_item(
                    unit, align=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                ),
            )

    def add_tracks(self, activities):
        """Make the activity list show this set of activities."""
        self.activities = activities
        self.activity_list_table.setRowCount(len(self.activities))
        for i, activity in enumerate(activities):
            link = self.assign_activity_items(activity.list_row, position=i)
            self.activities.link(activity, link)
        self.activity_list_table.resizeColumnsToContents()
        self.activity_list_table.sortItems(2, QtCore.Qt.DescendingOrder)

    def add_activity(self, activity_elements, position=0):
        """
        Add an activity to list.

        Returns the id of the first column of the added item for linking.
        """
        self.activity_list_table.insertRow(position)
        return self.assign_activity_items(activity_elements, position)

    def assign_activity_items(self, activity_elements, position=0):
        for j, content in enumerate(activity_elements):
            needs_special_sorting = False
            # Format as number
            if isinstance(content, tuple):
                needs_special_sorting = True
                content = self.unit_system.encode(*content)
            text = number_formats.list_format(
                content, self.activity_list_table.horizontalHeaderItem(j).text()
            )
            if needs_special_sorting:
                widget = create_table_item((content, text))
            else:
                widget = create_table_item(text)
            # Link activity to the first column so we can find it
            # when clicking
            self.activity_list_table.setItem(position, j, widget)
            if j == 0:
                return_link = id(widget)
        return return_link

    def update_splits(self, data):
        """Update the activity splits page."""
        self.split_table.setRowCount(len(data))
        for y, row in enumerate(data):
            for x, item in enumerate([(y + 1, None)] + row):
                if isinstance(item, tuple):
                    item = self.unit_system.encode(*item)
                self.split_table.setItem(
                    y,
                    x,
                    create_table_item(
                        (
                            item,
                            number_formats.split_format(
                                item, self.split_table.horizontalHeaderItem(x).text()
                            ),
                        ),
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                    ),
                )

    def update_page(self, page):
        """Switch to a new activity tab page."""
        if page in self.updated:
            return
        if page == 0:
            # Update labels, map and data box
            self.activity_name_label.setText(self.activity.name)
            self.flags_label.setText(" | ".join(self.activity.active_flags))
            self.date_time_label.setText(times.nice(self.activity.start_time))
            self.activity_type_label.setText(self.activity.sport)
            self.add_info(self.activity.stats)
            self.show_on_map(self.activity.track.lat_lon_list)
        elif page == 1:
            # Update charts
            if self.activity.track.has_altitude_data:
                self.charts["ele"].update(self.activity.track.alt_graph)
            self.charts["speed"].update(self.activity.track.speed_graph)
        elif page == 2:
            self.update_splits(
                self.activity.track.splits(
                    splitlength=self.unit_system.units["distance"].size
                )
            )
        elif page == 3:
            self.charts["zones"].update(
                self.activity.track.get_zone_durations(self.zones)
            )
        self.updated.add(page)

    def update_activity(self, selected):
        """Show a new activity on the right."""
        # Find the correct activity
        self.activity = self.activities.from_link(
            id(self.activity_list_table.item(selected, 0))
        )

        # Previously generated pages need refreshing
        self.updated = set()
        self.update_page(self.activity_tabs.currentIndex())

    def import_activity(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import an activity", "", "Activity Files (*.gpx *.fit)"
        )[0]
        if not filename:
            return
        new_activity = load_activity.import_and_load(filename)
        self.activity_list_table.setSortingEnabled(False)

        self.activities.add_activity(
            new_activity, self.add_activity(new_activity.create_unloaded().list_row)
        )
        self.activity_list_table.setCurrentCell(0, 0)
        self.activity_list_table.setSortingEnabled(True)

    def main_tab_switch(self, tab):
        if self.main_tabs.tabText(tab) == "Summary":
            self.total_distance_label.setText(
                number_formats.default_as_string(
                    self.unit_system.format(self.activities.total_distance, "distance")
                )
            )
            self.total_time_label.setText(
                number_formats.default_as_string(
                    self.unit_system.format(self.activities.total_time, "time")
                )
            )
            self.total_activities_label.setText(str(len(self.activities)))
            self.total_climb_label.setText(
                number_formats.default_as_string(
                    self.unit_system.format(self.activities.total_climb, "altitude")
                )
            )

    @property
    def unit_system(self):
        return units.UNIT_SYSTEMS[self.settings.unit_system]
