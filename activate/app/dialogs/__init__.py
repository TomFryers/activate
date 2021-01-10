"""Classes defining custom dialogs."""

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


class FormDialog(QtWidgets.QDialog):
    """A dialog consisiting of a form with OK and Cancel buttons."""

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
        if result == 1:
            return self.form.values()
        return result


def progress(parent, iterable, text, cancel_text="Cancel"):
    dialog = QtWidgets.QProgressDialog(text, cancel_text, 0, len(iterable), parent)
    dialog.setWindowModality(Qt.WindowModal)
    for done, value in enumerate(iterable):
        dialog.setValue(done)
        if dialog.wasCanceled():
            return
        yield value
    dialog.setValue(len(iterable))
