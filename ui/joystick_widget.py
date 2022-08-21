import sys
from enum import Enum
from math import cos, sin

from PySide6 import QtWidgets
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QMainWindow,
    QStyleFactory,
    QWidget,
)


class Direction(Enum):
    Left = 0
    Right = 1
    Up = 2
    Down = 3


class Joystick(QtWidgets.QWidget):
    stick_signal = Signal(float,float)

    def __init__(self, parent=None):
        super(Joystick, self).__init__(parent)
        self.setMinimumSize(100, 100)
        self.movingOffset = QPointF(0, 0)
        self.grabCenter = False
        self.gamepadControl = False
        self.bef_r = 0
        self.bef_r_ = 0
        self.__maxDistance = 28  # ゲームパッド操作を反映させるときの倍率に等しい
        self.angle = 0
        self.distance = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        bounds = QRectF(
            -self.__maxDistance, -self.__maxDistance, self.__maxDistance * 2, self.__maxDistance * 2
        ).translated(self._center())
        painter.drawEllipse(bounds)
        painter.setBrush(QColor(65, 69, 72))
        painter.drawEllipse(self._centerEllipse())

    def _centerEllipse(self):
        if self.grabCenter or self.gamepadControl:
            return QRectF(-24, -24, 48, 48).translated(self.movingOffset)
        return QRectF(-24, -24, 48, 48).translated(self._center())

    def _center(self):
        return QPointF(self.width() / 2, self.height() / 2)

    def _boundJoystick(self, point):
        limitLine = QLineF(self._center(), point)
        if limitLine.length() > self.__maxDistance:
            limitLine.setLength(self.__maxDistance)
        return limitLine.p2()

    def joystickDirection(self):
        # print(self.movingOffset)
        if not self.grabCenter:
            return 0
        normVector = QLineF(self._center(), self.movingOffset)
        currentDistance = normVector.length()
        self.angle = normVector.angle()
        # print(self.angle)

        self.distance = min(currentDistance / self.__maxDistance, 1.0)
        if 45 <= self.angle < 135:
            return (Direction.Up, self.distance)
        elif 135 <= self.angle < 225:
            return (Direction.Left, self.distance)
        elif 225 <= self.angle < 315:
            return (Direction.Down, self.distance)
        return (Direction.Right, self.distance)

    def mousePressEvent(self, ev):
        self.grabCenter = self._centerEllipse().contains(ev.position())
        return super().mousePressEvent(ev)

    def mouseReleaseEvent(self, event):
        self.grabCenter = False
        self.movingOffset = QPointF(0, 0)
        self.update()
        self.stick_signal.emit(0, 0)

    def mouseMoveEvent(self, event):
        if self.grabCenter:
            # print("Moving")
            self.movingOffset = self._boundJoystick(event.position())
            self.update()
        self.joystickDirection()
        # print(self.angle, self.distance)
        self.stick_signal.emit(self.angle, self.distance)

    def stickMoveEvent(self, r, a):
        if r > 0:
            self.gamepadControl = True
            x = self.__maxDistance * r * cos(a) + 60  # ウィジェットの半幅を加算
            y = self.__maxDistance * r * sin(a) + 60  # ウィジェットの半高を加算
            # print(x, y)
        elif self.bef_r_ > 0 and r == 0:
            self.gamepadControl = False
            self.movingOffset = QPointF(0, 0)
            self.update()

        # print("Moving")
        if self.gamepadControl:
            self.movingOffset = self._boundJoystick(QPointF(x, y))
            self.update()
        # print(self.joystickDirection())

        self.bef_r_ = r


if __name__ == "__main__":
    # Create main application window
    app = QApplication()
    mw = QMainWindow()
    mw.setWindowTitle("Joystick example")

    # Create and set widget layout
    # Main widget container
    cw = QWidget()
    ml = QGridLayout()
    cw.setLayout(ml)
    mw.setCentralWidget(cw)

    # Create joystick
    joystick = Joystick()

    # ml.addLayout(joystick.get_joystick_layout(),0,0)
    ml.addWidget(joystick, 0, 0)

    mw.show()

    sys.exit(app.exec())
