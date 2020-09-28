"""Classes defining custom dialogs."""

from PyQt5 import QtWidgets


class FormDialog(QtWidgets.QDialog):
    def __init__(self, form, *args, **kwargs):
        self.form = form
        super().__init__(*args, **kwargs)
        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.main_layout.addLayout(self.form)

        self.buttons = QtWidgets.QDialogButtonBox(self)
        self.buttons.setStandardButtons(self.buttons.Cancel | self.buttons.Ok)

        self.main_layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def exec(self, initial_values: dict):
        self.form.set_values(initial_values)
        result = super().exec()
        if not result:
            return None
        elif result == 1:
            return self.form.values()
        return result
