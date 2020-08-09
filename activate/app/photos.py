from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from activate.app import paths


class ClickablePhoto(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(int)
    deleted = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.menu = QtWidgets.QMenu(self)
        self.action_delete = QtWidgets.QAction("Delete")
        self.action_delete.setIcon(QtGui.QIcon.fromTheme("edit-delete"))
        self.action_delete.triggered.connect(self.delete)
        self.menu.addAction(self.action_delete)

    @property
    def index(self):
        return self.parent().layout().indexOf(self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self.menu.exec(event.globalPos())

    def delete(self):
        self.deleted.emit(self.index)


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
        self.filenames = filenames
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
            label = ClickablePhoto(self)
            label.setPixmap(photo)
            label.deleted.connect(self.delete)
            label.clicked.connect(self.show_photos)
            self.layout().addWidget(label)
            self.labels.append(label)

    def show_photos(self, index):
        viewer = PhotoViewer(self.filenames, index)
        viewer.exec()

    def show_activity_photos(self, activity):
        self.activity = activity
        self.replace_photos(activity.photos)

    def delete(self, index):
        self.filenames.pop(index)
        self.photos.pop(index)
        self.replace_photos(self.filenames)
        self.activity.photos = self.filenames
        self.activity.save(paths.ACTIVITIES)


class PhotoViewer(QtWidgets.QDialog):
    def __init__(self, photos, current_index, *args, **kwargs):
        self.filenames = photos.copy()
        self.current_index = current_index
        self.photos = photos
        super().__init__(*args, **kwargs)
        self.label = QtWidgets.QLabel(self)
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.label, alignment=Qt.AlignCenter)
        self.show_photo()

    def show_photo(self):
        photo = self.photos[self.current_index]
        if not isinstance(photo, QtGui.QPixmap):
            photo = QtGui.QPixmap(photo)
            photo = photo.scaled(
                self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.photos[self.current_index] = photo
        self.label.setPixmap(photo)

    def set_new_index(self, index):
        self.current_index = index
        self.current_index %= len(self.photos)
        self.show_photo()

    def keyPressEvent(self, event):
        print(event.key())
        if event.key() in {Qt.Key_Right, Qt.Key_Space}:
            self.set_new_index(self.current_index + 1)
            return
        if event.key() in {Qt.Key_Left, Qt.Key_Backspace}:
            self.set_new_index(self.current_index - 1)
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.photos = self.filenames.copy()
        self.show_photo()
