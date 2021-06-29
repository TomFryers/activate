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
        if result == self.Accepted:
            return self.form.values()
        return result


def progress(parent, iterable, text, length=None, cancel_text="Cancel"):
    if length is None:
        length = len(iterable)
    dialog = QtWidgets.QProgressDialog(text, cancel_text, 0, length, parent)
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setMinimumDuration(0)
    for done, value in enumerate(iterable):
        dialog.setValue(done)
        QtWidgets.qApp.processEvents()
        if dialog.wasCanceled():
            return
        yield value
    dialog.setValue(length)
