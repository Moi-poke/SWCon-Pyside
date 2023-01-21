from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QGraphicsView


class View(QGraphicsView):
    template_matching = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.pen = QPen()
        self.pen.setColor(Qt.red)
        self.start = QPoint()
        self.end = QPoint()
        self.setMouseTracking(True)
        self.mousePressed = False
        self.rect, self.line = None, None

    def draw_shape(self):
        if self.start.isNull() or self.end.isNull():
            return
        if self.start.x() == self.end.x() and self.start.y() == self.end.y():
            return
        elif abs(self.end.x() - self.start.x()) < 2 or abs(self.end.y() - self.start.y()) < 2:
            if self.rect is not None:
                self.scene().removeItem(self.rect)
                self.rect = None
            if abs(self.end.y() - self.start.y()) < 2:
                # draw vertical line
                if self.line is not None:
                    self.line.setLine(self.start.x(), self.start.y(), self.end.x(), self.start.y())
                else:
                    self.line = self.scene().addLine(self.start.x(), self.start.y(), self.end.x(), self.start.y(),
                                                     self.pen)
            else:
                # draw horizontal line
                if self.line is not None:
                    self.line.setLine(self.start.x(), self.start.y(), self.start.x(), self.end.y())
                else:
                    self.line = self.scene().addLine(self.start.x(), self.start.y(), self.start.x(), self.end.y(),
                                                     self.pen)
        else:
            if self.line is not None:
                self.scene().removeItem(self.line)
                self.line = None

            width = abs(self.start.x() - self.end.x())
            height = abs(self.start.y() - self.end.y())
            if self.rect is None:
                self.rect = self.scene().addRect(min(self.start.x(), self.end.x()), min(self.start.y(), self.end.y()),
                                                 width, height, self.pen)
            else:
                self.rect.setRect(min(self.start.x(), self.end.x()), min(self.start.y(), self.end.y()), width, height)

    def remove_object(self):
        self.line = None
        self.rect = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            try:
                self.mousePressed = True
                self.scene().removeItem(self.line)
                self.scene().removeItem(self.rect)
                self.start = self.mapToScene(event.pos())
            except RuntimeError:
                self.line = None
                self.rect = None

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton & self.mousePressed:
            self.end = self.mapToScene(event.pos())
            self.draw_shape()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.mousePressed:
            self.mousePressed = False
            self.draw_shape()
            # self.start, self.end = QPoint(), QPoint()
            # self.rect, self.line = None, None
            # print(self.start, self.end)
            self.template_matching.emit()
