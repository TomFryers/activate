from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt


class PhotoList(QtWidgets.QWidget):
    """A container for photos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLayout = QtWidgets.QHBoxLayout(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.width = event.size().width()
        self.height = event.size().height()

    def empty(self):
        """Remove all photos in the PhotoList."""
        for index in range(self.layout().count() - 1, -1, -1):
            self.layout().itemAt(index).widget().setParent(None)

    def replace_photos(self, filenames):
        """Replace the photos with new ones."""
        self.empty()
        if not filenames:
            return
        self.photos = [QtGui.QPixmap(f) for f in filenames]
        total_aspect = sum(i.width() / i.height() for i in self.photos)
        width = (
            self.width
            - self.layout().spacing() * (len(self.photos) - 1)
            - self.layout().contentsMargins().left()
            - self.layout().contentsMargins().right()
        )
        height = width / total_aspect
        self.photos = [
            p.scaledToHeight(height, Qt.SmoothTransformation) for p in self.photos
        ]
        self.labels = []
        for photo in self.photos:
            label = QtWidgets.QLabel(self)
            label.setPixmap(photo)
            self.layout().addWidget(label)
            self.labels.append(label)
