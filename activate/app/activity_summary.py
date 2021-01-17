"""Display an individual activity's data."""
import markdown
from PyQt5 import QtWidgets

from activate import times
from activate.app import photos
from activate.app.ui.activity_summary import Ui_activity_summary


class ActivitySummary(QtWidgets.QWidget, Ui_activity_summary):
    """A one-page activity summary."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setup(self, unit_system, map_widget):
        self.unit_system = unit_system
        self.map_widget = map_widget
        self.updated = set()
        self.photo_list = photos.PhotoList(self)
        self.activity_summary_layout.addWidget(self.photo_list, 1, 1)
        self.info_table.set_units(self.unit_system)

    def update(self):
        """Update labels, map and data box."""
        self.activity_name_label.setText(self.activity.name)
        self.flags_label.setText(" | ".join(self.activity.active_flags))
        self.description_label.setText(markdown.markdown(self.activity.description))
        self.date_time_label.setText(times.nice(self.activity.start_time))
        self.activity_type_label.setText(self.activity.sport)
        self.info_table.update_data(self.activity.stats)
        if self.activity.track.has_position_data:
            self.map_widget.setVisible(True)
            self.map_widget.show_route(self.activity.track.lat_lon_list)
            self.show_map()
        else:
            self.map_widget.setVisible(False)
        self.photo_list.show_activity_photos(self.activity)

    def show_activity(self, new_activity):
        """Display a new activity."""
        self.activity = new_activity
        self.update()

    def show_map(self):
        """
        Take back the map widget.

        This is necessary because the map widget must be shared between
        all layouts, and a widget cannot be in multiple places at once.
        Call this when the activity summary becomes visible.
        """
        self.map_container.addWidget(self.map_widget)
