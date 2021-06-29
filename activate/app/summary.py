from collections import Counter
from datetime import datetime

from PyQt5 import QtWidgets

from activate import activity_types, number_formats
from activate.app import charts
from activate.app.dialogs import progress
from activate.app.ui.summary import Ui_summary

NOW = datetime.now()


class Summary(QtWidgets.QWidget, Ui_summary):
    """A widget summarising all of a person's activities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setup(self, unit_system, map_widget, activities):
        self.unit_system = unit_system
        self.map_widget = map_widget
        self.activities = activities
        # This has to be added here so when the heatmap is switched to,
        # the widget is already 'there', so it has a size. This lets
        # fitBounds work properly.
        self.heatmap_layout.addWidget(self.map_widget)
        self.records_table.set_units(self.unit_system)
        self.summary_period = "Year"
        self.progression_chart.set_units(self.unit_system)
        self.update_activity_types_list()
        self.eddington_chart = charts.LineChart(
            self.eddington_chart_widget,
            self.unit_system,
            series_count=2,
            vertical_log=True,
        )
        self.eddington_chart.y_axis.setTitleText("Count")
        self.eddington_chart.add_legend(("Done", "Target"))

    def update_activity_types_list(self):
        """Set up activity types list for the summary page."""
        self.activity_types_list.row_names = [
            x[0] for x in Counter(a.sport for a in self.activities).most_common()
        ]
        self.activity_types_list.add_all_row()
        self.activity_types_list.check_all()

    def summary_tab_switch(self):
        tab = self.summary_tabs.tabText(self.summary_tabs.currentIndex())
        {
            "Totals": self.update_totals,
            "Records": self.update_records,
            "Progression": self.update_progression,
            "Gallery": self.update_gallery,
            "Heatmap": self.update_heatmap,
            "Eddington": self.update_eddington,
        }[tab]()

    def update_progression(self):
        """Update the progression chart."""
        self.progression_chart.update(
            self.summary_period,
            self.get_allowed_for_summary(),
            now=NOW,
            activities=self.activities,
        )

    def get_allowed_for_summary(self):
        """Get the allowed activity types from the checklist."""
        return set(self.activity_types_list.checked_rows)

    def set_formatted_number_label(self, label, value, dimension):
        """Set a label to a number, formatted with the correct units."""
        label.setText(
            number_formats.default_as_string(self.unit_system.format(value, dimension))
        )

    def update_totals(self):
        """Update the summary page totals."""
        allowed_activity_types = self.get_allowed_for_summary()
        allowed_activities = list(
            self.activities.filtered(allowed_activity_types, self.summary_period, NOW)
        )
        self.set_formatted_number_label(
            self.total_distance_label,
            self.activities.total_distance(allowed_activities),
            "distance",
        )
        self.set_formatted_number_label(
            self.total_time_label,
            self.activities.total_time(allowed_activities),
            "time",
        )
        self.total_activities_label.setText(
            str(self.activities.total_activities(allowed_activities))
        )
        self.set_formatted_number_label(
            self.total_climb_label,
            self.activities.total_climb(allowed_activities),
            "altitude",
        )

    def update_records(self):
        good_distances = {}
        for sport in self.get_allowed_for_summary():
            good_distances.update(
                activity_types.SPECIAL_DISTANCES[sport]
                if sport in activity_types.SPECIAL_DISTANCES
                else activity_types.SPECIAL_DISTANCES[None]
            )
        good_distances = {k: good_distances[k] for k in sorted(good_distances)}
        records, activity_ids = self.activities.get_records(
            self.get_allowed_for_summary(),
            self.summary_period,
            NOW,
            good_distances,
            lambda x: progress(self, list(x), "Loading"),
        )
        try:
            first_non_one_second = max(
                next(
                    i for i, r in enumerate(records) if r[1].value.total_seconds() > 1
                ),
                1,
            )
        except StopIteration:
            first_non_one_second = 0
        records = records[first_non_one_second - 1 :]
        activity_ids = list(activity_ids)[first_non_one_second - 1 :]
        good_distances = list(good_distances.values())[first_non_one_second - 1 :]
        self.records_table.update_data(good_distances, records, activity_ids)

    def update_gallery(self):
        self.gallery.replace_photos(
            self.activities.get_all_photos(
                self.get_allowed_for_summary(), self.summary_period, NOW
            )
        )

    def update_heatmap(self):
        self.heatmap_layout.addWidget(self.map_widget)
        self.map_widget.show_heatmap(
            self.activities.get_all_routes(
                self.get_allowed_for_summary(),
                self.summary_period,
                NOW,
                lambda x: progress(self, list(x), "Loading"),
            )
        )

    def update_eddington(self):
        allowed_activities = list(
            self.activities.filtered(
                self.get_allowed_for_summary(), self.summary_period, NOW
            )
        )
        if not allowed_activities:
            return
        unit = self.unit_system.units["distance"].size
        eddington_data = self.activities.eddington(
            allowed_activities, lambda x: progress(self, list(x), "Loading")
        )
        eddington_number = 0
        for eddington_number in range(1, len(eddington_data) + 1):
            if eddington_data[eddington_number - 1] <= eddington_number * unit:
                break
        self.total_eddington_label.setText(
            f"{eddington_number} {self.unit_system.units['distance'].symbol}"
        )
        y_indices = list(range(1, len(eddington_data) + 1))
        x_indices = [x * unit for x in y_indices[: int(eddington_data[0] / unit) + 1]]
        y_indices = (y_indices, None)
        self.eddington_chart.update(
            (
                ((eddington_data, "distance"), y_indices),
                ((x_indices, "distance"), y_indices),
            )
        )

    def summary_period_changed(self, value):
        self.summary_period = value
        self.summary_tab_switch()
