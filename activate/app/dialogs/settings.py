import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from activate.app import connect, settings, widgets
from activate.app.dialogs import FormDialog
from activate.app.ui.settings import Ui_settings
from activate.app.widgets import Form


class AddServerDialog(FormDialog):
    def __init__(self, *args, **kwargs):
        layout = {
            "Address": QtWidgets.QLineEdit(),
            "Name": QtWidgets.QLineEdit(),
            "Username": QtWidgets.QLineEdit(),
            "Password": QtWidgets.QLineEdit(),
        }
        layout["Password"].setEchoMode(layout["Password"].Password)
        super().__init__(*args, form=Form(layout), **kwargs)
        self.setWindowTitle("Add Server")


class SettingsDialog(QtWidgets.QDialog, Ui_settings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.settings_tabs.setTabIcon(0, QIcon.fromTheme("measure"))
        self.settings_tabs.setTabIcon(1, QIcon.fromTheme("network-server"))
        self.add_server_button.setIcon(PyQt5.QtGui.QIcon.fromTheme("list-add"))
        self.custom_units = widgets.CustomUnits(self)
        self.units_tab_layout.addLayout(self.custom_units)
        self.units_tab_layout.setAlignment(Qt.AlignTop)

    def add_server(self):
        result = AddServerDialog().exec({})
        if not result:
            return
        self.server_table.add_row()
        self.server_table.set_server(
            self.server_table.rowCount() - 1, connect.Server(*result.values())
        )

    def load_from_settings(self, current_settings: settings.Settings):
        """Load a Settings object to the UI widgets."""
        self.unit_system.setCurrentText(current_settings.unit_system)
        self.server_table.set_servers(current_settings.servers)
        self.custom_units.set_units(current_settings.custom_units)

    def get_settings(self) -> settings.Settings:
        """Get a Settings object from the UI widgets."""
        return settings.Settings(
            unit_system=self.unit_system.currentText(),
            servers=self.server_table.get_servers(),
            custom_units=self.custom_units.units_dict(),
        )

    def exec(self, current_settings, page):
        self.settings_tabs.setCurrentIndex(("Units", "Servers").index(page))
        self.load_from_settings(current_settings)
        result = super().exec()
        if not result:
            return current_settings
        new_settings = self.get_settings()
        new_settings.save()
        return new_settings
