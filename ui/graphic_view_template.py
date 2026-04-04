from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPen, QColor
from PySide6.QtWidgets import QGraphicsView


class View(QGraphicsView):
    template_matching = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.pen = QPen()
        self.pen.setColor(QColor(255, 0, 0))
        self.start = QPointF()
        self.end = QPointF()
        self.setMouseTracking(True)
        self.mousePressed = False
        self.rect = None
        self.line = None

    def draw_shape(self):
        if self.start.isNull() or self.end.isNull():
            return

        if self.start.x() == self.end.x() and self.start.y() == self.end.y():
            return

        scene = self.scene()
        if scene is None:
            return

        if (
            abs(self.end.x() - self.start.x()) < 2
            or abs(self.end.y() - self.start.y()) < 2
        ):
            if self.rect is not None:
                scene.removeItem(self.rect)
                self.rect = None

            if abs(self.end.y() - self.start.y()) < 2:
                # 横線
                if self.line is not None:
                    self.line.setLine(
                        self.start.x(),
                        self.start.y(),
                        self.end.x(),
                        self.start.y(),
                    )
                else:
                    self.line = scene.addLine(
                        self.start.x(),
                        self.start.y(),
                        self.end.x(),
                        self.start.y(),
                        self.pen,
                    )
            else:
                # 縦線
                if self.line is not None:
                    self.line.setLine(
                        self.start.x(),
                        self.start.y(),
                        self.start.x(),
                        self.end.y(),
                    )
                else:
                    self.line = scene.addLine(
                        self.start.x(),
                        self.start.y(),
                        self.start.x(),
                        self.end.y(),
                        self.pen,
                    )
        else:
            if self.line is not None:
                scene.removeItem(self.line)
                self.line = None

            width = abs(self.start.x() - self.end.x())
            height = abs(self.start.y() - self.end.y())

            if self.rect is None:
                self.rect = scene.addRect(
                    min(self.start.x(), self.end.x()),
                    min(self.start.y(), self.end.y()),
                    width,
                    height,
                    self.pen,
                )
            else:
                self.rect.setRect(
                    min(self.start.x(), self.end.x()),
                    min(self.start.y(), self.end.y()),
                    width,
                    height,
                )

    def remove_object(self):
        scene = self.scene()
        if scene is None:
            self.line = None
            self.rect = None
            return

        if self.line is not None:
            scene.removeItem(self.line)
            self.line = None

        if self.rect is not None:
            scene.removeItem(self.rect)
            self.rect = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePressed = True
            self.remove_object()
            self.start = self.mapToScene(event.pos())
            self.end = self.start

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mousePressed and (event.buttons() & Qt.MouseButton.LeftButton):
            self.end = self.mapToScene(event.pos())
            self.draw_shape()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.mousePressed:
            self.mousePressed = False
            self.end = self.mapToScene(event.pos())
            self.draw_shape()
            self.template_matching.emit()

        super().mouseReleaseEvent(event)
