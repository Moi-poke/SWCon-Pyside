#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import math
import queue
import time
from collections import OrderedDict
from enum import Enum, IntEnum, IntFlag, auto
from logging import DEBUG, NullHandler, getLogger
from typing import Any, Optional


class Button(IntFlag):
    Y = auto()
    B = auto()
    A = auto()
    X = auto()
    L = auto()
    R = auto()
    ZL = auto()
    ZR = auto()
    MINUS = auto()
    PLUS = auto()
    LCLICK = auto()
    RCLICK = auto()
    HOME = auto()
    CAPTURE = auto()


class Hat(IntEnum):
    TOP = 0
    TOP_RIGHT = 1
    RIGHT = 2
    BTM_RIGHT = 3
    BTM = 4
    BTM_LEFT = 5
    LEFT = 6
    TOP_LEFT = 7
    CENTER = 8


class Stick(Enum):
    LEFT = auto()
    RIGHT = auto()


class Tilt(Enum):
    UP = auto()
    RIGHT = auto()
    DOWN = auto()
    LEFT = auto()
    R_UP = auto()
    R_RIGHT = auto()
    R_DOWN = auto()
    R_LEFT = auto()


MINIMUM = 0
CENTER = 128
MAXIMUM = 255


class SendFormat:
    def __init__(self) -> None:
        self._logger = getLogger(__name__)
        self._logger.addHandler(NullHandler())
        self._logger.setLevel(DEBUG)
        self._logger.propagate = True

        self.format = OrderedDict(
            [
                ("btn", 0),
                ("hat", Hat.CENTER),
                ("lx", CENTER),
                ("ly", CENTER),
                ("rx", CENTER),
                ("ry", CENTER),
            ]
        )
        self.L_stick_changed = False
        self.R_stick_changed = False
        self.Hat_pos = Hat.CENTER

    def setButton(self, btns: list[Button]) -> None:
        for btn in btns:
            self.format["btn"] |= int(btn)

    def unsetButton(self, btns: list[Button]) -> None:
        for btn in btns:
            self.format["btn"] &= ~int(btn)

    def resetAllButtons(self) -> None:
        self.format["btn"] = 0

    def setHat(self, btns: list[Hat]) -> None:
        if not btns:
            self.format["hat"] = self.Hat_pos
            return
        self.Hat_pos = btns[0]
        self.format["hat"] = btns[0]

    def unsetHat(self) -> None:
        self.Hat_pos = Hat.CENTER
        self.format["hat"] = Hat.CENTER

    def setAnyDirection(self, dirs: list["Direction"]) -> None:
        for direction in dirs:
            if direction.stick == Stick.LEFT:
                if (
                    self.format["lx"] != direction.x
                    or self.format["ly"] != 255 - direction.y
                ):
                    self.L_stick_changed = True
                self.format["lx"] = direction.x
                self.format["ly"] = 255 - direction.y
            elif direction.stick == Stick.RIGHT:
                if (
                    self.format["rx"] != direction.x
                    or self.format["ry"] != 255 - direction.y
                ):
                    self.R_stick_changed = True
                self.format["rx"] = direction.x
                self.format["ry"] = 255 - direction.y

    def unsetDirection(self, dirs: list[Tilt]) -> None:
        if Tilt.UP in dirs or Tilt.DOWN in dirs:
            self.format["ly"] = CENTER
            self.format["lx"] = self.fixOtherAxis(self.format["lx"])
            self.L_stick_changed = True
        if Tilt.RIGHT in dirs or Tilt.LEFT in dirs:
            self.format["lx"] = CENTER
            self.format["ly"] = self.fixOtherAxis(self.format["ly"])
            self.L_stick_changed = True
        if Tilt.R_UP in dirs or Tilt.R_DOWN in dirs:
            self.format["ry"] = CENTER
            self.format["rx"] = self.fixOtherAxis(self.format["rx"])
            self.R_stick_changed = True
        if Tilt.R_RIGHT in dirs or Tilt.R_LEFT in dirs:
            self.format["rx"] = CENTER
            self.format["ry"] = self.fixOtherAxis(self.format["ry"])
            self.R_stick_changed = True

    @staticmethod
    def fixOtherAxis(fix_target: int) -> int:
        if fix_target == CENTER:
            return CENTER
        return 0 if fix_target < CENTER else 255

    def resetAllDirections(self) -> None:
        self.format["lx"] = CENTER
        self.format["ly"] = CENTER
        self.format["rx"] = CENTER
        self.format["ry"] = CENTER
        self.L_stick_changed = True
        self.R_stick_changed = True
        self.Hat_pos = Hat.CENTER

    def convert2str(self) -> str:
        send_btn = int(self.format["btn"]) << 2
        str_L = ""
        str_R = ""
        str_hat = str(int(self.format["hat"]))

        if self.L_stick_changed:
            send_btn |= 0x2
            str_L = f"{format(self.format['lx'], 'x')} {format(self.format['ly'], 'x')}"
        if self.R_stick_changed:
            send_btn |= 0x1
            str_R = f"{format(self.format['rx'], 'x')} {format(self.format['ry'], 'x')}"

        s = format(send_btn, "#06x")
        s += f" {str_hat}"
        if self.L_stick_changed:
            s += f" {str_L}"
        if self.R_stick_changed:
            s += f" {str_R}"

        self.L_stick_changed = False
        self.R_stick_changed = False
        return s


class Direction:
    UP: Any
    RIGHT: Any
    DOWN: Any
    LEFT: Any
    UP_RIGHT: Any
    DOWN_RIGHT: Any
    DOWN_LEFT: Any
    UP_LEFT: Any
    R_UP: Any
    R_RIGHT: Any
    R_DOWN: Any
    R_LEFT: Any
    R_UP_RIGHT: Any
    R_DOWN_RIGHT: Any
    R_DOWN_LEFT: Any
    R_UP_LEFT: Any

    def __init__(
        self,
        stick: Stick,
        angle: int | float | tuple[int, int],
        magnification: int | float = 1.0,
        isDegree: bool = True,
        showName: Optional[str] = None,
    ) -> None:
        self._logger = getLogger(__name__)
        self._logger.addHandler(NullHandler())
        self._logger.setLevel(DEBUG)
        self._logger.propagate = True

        self.stick = stick
        self.angle_for_show = angle
        self.showName = showName

        if magnification > 1.0:
            self.mag = 1.0
        elif magnification < 0:
            self.mag = 0.0
        else:
            self.mag = float(magnification)

        if isinstance(angle, tuple):
            self.x = int(angle[0])
            self.y = int(angle[1])
            self.showName = f"({self.x}, {self.y})"
        else:
            rad = math.radians(angle) if isDegree else angle
            self.x = math.ceil(127.5 * math.cos(rad) * self.mag + 127.5)
            self.y = math.floor(127.5 * math.sin(rad) * self.mag + 127.5)

    def __repr__(self) -> str:
        if self.showName:
            return f"<{self.stick}, {self.showName}>"
        return f"<{self.stick}, {self.angle_for_show}[deg]>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Direction):
            return False
        return self.stick == other.stick and self.angle_for_show == other.angle_for_show

    def getTilting(self) -> list[Tilt]:
        tilting: list[Tilt] = []
        if self.stick == Stick.LEFT:
            if self.x < CENTER:
                tilting.append(Tilt.LEFT)
            elif self.x > CENTER:
                tilting.append(Tilt.RIGHT)
            if self.y < CENTER - 1:
                tilting.append(Tilt.DOWN)
            elif self.y > CENTER - 1:
                tilting.append(Tilt.UP)
        elif self.stick == Stick.RIGHT:
            if self.x < CENTER:
                tilting.append(Tilt.R_LEFT)
            elif self.x > CENTER:
                tilting.append(Tilt.R_RIGHT)
            if self.y < CENTER - 1:
                tilting.append(Tilt.R_DOWN)
            elif self.y > CENTER - 1:
                tilting.append(Tilt.R_UP)
        return tilting


Direction.UP = Direction(Stick.LEFT, 90, showName="UP")
Direction.RIGHT = Direction(Stick.LEFT, 0, showName="RIGHT")
Direction.DOWN = Direction(Stick.LEFT, -90, showName="DOWN")
Direction.LEFT = Direction(Stick.LEFT, -180, showName="LEFT")
Direction.UP_RIGHT = Direction(Stick.LEFT, 45, showName="UP_RIGHT")
Direction.DOWN_RIGHT = Direction(Stick.LEFT, -45, showName="DOWN_RIGHT")
Direction.DOWN_LEFT = Direction(Stick.LEFT, -135, showName="DOWN_LEFT")
Direction.UP_LEFT = Direction(Stick.LEFT, 135, showName="UP_LEFT")

Direction.R_UP = Direction(Stick.RIGHT, 90, showName="UP")
Direction.R_RIGHT = Direction(Stick.RIGHT, 0, showName="RIGHT")
Direction.R_DOWN = Direction(Stick.RIGHT, -90, showName="DOWN")
Direction.R_LEFT = Direction(Stick.RIGHT, -180, showName="LEFT")
Direction.R_UP_RIGHT = Direction(Stick.RIGHT, 45, showName="UP_RIGHT")
Direction.R_DOWN_RIGHT = Direction(Stick.RIGHT, -45, showName="DOWN_RIGHT")
Direction.R_DOWN_LEFT = Direction(Stick.RIGHT, -135, showName="DOWN_LEFT")
Direction.R_UP_LEFT = Direction(Stick.RIGHT, 135, showName="UP_LEFT")


class KeyPress:
    def __init__(self, ser) -> None:
        self._logger = getLogger(__name__)
        self._logger.addHandler(NullHandler())
        self._logger.setLevel(DEBUG)
        self._logger.propagate = True

        self.q = queue.Queue()
        self.ser = ser
        self.format = SendFormat()
        self.holdButton: list[Button | Hat | Direction] = []
        self.NEUTRAL = dict(self.format.format)

        self.input_time_0 = time.perf_counter()
        self.input_time_1 = time.perf_counter()
        self.inputEnd_time_0 = time.perf_counter()
        self.was_neutral = True

    def input(self, btns, overwrite: bool = False, ifPrint: bool = True) -> None:
        _ = ifPrint
        if not isinstance(btns, list):
            btns = [btns]

        for btn in self.holdButton:
            if btn not in btns:
                btns.append(btn)

        if overwrite:
            self.format.resetAllButtons()
            self.format.unsetHat()
            self.format.resetAllDirections()

        self.format.setButton([btn for btn in btns if isinstance(btn, Button)])
        self.format.setHat([btn for btn in btns if isinstance(btn, Hat)])
        self.format.setAnyDirection([btn for btn in btns if isinstance(btn, Direction)])
        self.ser.writeRow(self.format.convert2str())

    def inputEnd(self, buttons, ifPrint: bool = True, unset_hat: bool = True) -> None:
        _ = ifPrint
        if not isinstance(buttons, list):
            buttons = [buttons]

        tilts: list[Tilt] = []
        for direction in [btn for btn in buttons if isinstance(btn, Direction)]:
            tilts.extend(direction.getTilting())

        self.format.unsetButton([btn for btn in buttons if isinstance(btn, Button)])
        if unset_hat:
            self.format.unsetHat()
        self.format.unsetDirection(tilts)
        self.ser.writeRow(self.format.convert2str())

    def hold(self, buttons) -> None:
        if not isinstance(buttons, list):
            buttons = [buttons]
        for btn in buttons:
            if btn in self.holdButton:
                self._logger.warning(
                    "%s is already in holding state", getattr(btn, "name", btn)
                )
                return
            self.holdButton.append(btn)
        self.input(buttons)

    def holdEnd(self, buttons) -> None:
        if not isinstance(buttons, list):
            buttons = [buttons]
        for btn in buttons:
            if btn in self.holdButton:
                self.holdButton.remove(btn)
        self.inputEnd(buttons)

    def end(self) -> None:
        self.ser.writeRow("end")
