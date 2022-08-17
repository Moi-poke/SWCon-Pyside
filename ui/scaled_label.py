# custom_widgets.py

from PySide6 import QtCore, QtGui, QtWidgets


class ScaledLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        QtWidgets.QLabel.__init__(self)
        self._pixmap = self.pixmap()
        self._resized = False

    def resizeEvent(self, event):
        self.setPixmap(self._pixmap)

    def setPixmap(self, pixmap):  # overriding setPixmap
        if not pixmap:
            return
        self._pixmap = pixmap
        return QtWidgets.QLabel.setPixmap(self, self._pixmap.scaled(self.frameSize(), QtCore.Qt.KeepAspectRatio))
