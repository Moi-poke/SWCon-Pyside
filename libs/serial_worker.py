from __future__ import annotations

import logging
import math
import time
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Signal, Slot, QTimer, Qt
from libs.gui_stick_store import GuiStickStore


from libs.keys import Button, Direction, Hat, Stick
from libs.sender import Sender


class SerialWorker(QObject):
    log = Signal(str, int)
    serial_state_changed = Signal(bool, str)
    serial_error = Signal(str)

    def __init__(
        self,
        is_show_serial: bool = False,
        keypress_factory: Optional[Callable[[Sender], Any]] = None,
        gui_stick_store: Optional[GuiStickStore] = None,
        parent: Optional[QObject] = None,
    ) -> None:

        super().__init__(parent)

        self._sender = Sender(is_show_serial=is_show_serial, if_print=False)
        self._sender.print_strings.connect(self.log.emit)

        self._keypress_factory = keypress_factory
        self._keypress: Optional[Any] = None
        self._is_open = False
        self._port_label = ""

        self._gamepad_axis = (0.0, 0.0, 0.0, 0.0)
        self._gui_left: Optional[Direction] = None
        self._gui_right: Optional[Direction] = None
        self._dead_zone = 0.35

        self._gui_stick_store = gui_stick_store
        self._poll_timer: Optional[QTimer] = None
        self._last_stick_state: Optional[tuple[object, object]] = None

    @property
    def sender_instance(self) -> Sender:
        return self._sender

    @Slot(bool)
    def set_show_serial(self, enabled: bool) -> None:
        self._sender.is_show_serial = bool(enabled)

    @Slot()
    def start(self) -> None:
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._poll_timer.setInterval(16)  # 約60Hz
            self._poll_timer.timeout.connect(self._poll_latest_inputs)

        self._poll_timer.start()

    @Slot(object, str)
    def open_port(self, port_num: object, port_name: str = "") -> None:
        try:
            ok = self._sender.openSerial(port_num, port_name)
            if not ok:
                self._is_open = False
                self._port_label = ""
                self.serial_state_changed.emit(False, "")
                return

            self._is_open = True
            self._port_label = port_name if port_name else str(port_num)

            if self._keypress_factory is not None:
                self._keypress = self._keypress_factory(self._sender)

            self.serial_state_changed.emit(True, self._port_label)
            self.log.emit(f"Serial opened: {self._port_label}", logging.INFO)

            if self._keypress is not None:
                try:
                    self._keypress.input([], overwrite=True)
                except Exception as exc:
                    self.log.emit(
                        f"Failed to send neutral after open: {exc}", logging.WARNING
                    )

        except Exception as exc:
            self._is_open = False
            self._port_label = ""
            self._keypress = None
            self.serial_error.emit(str(exc))
            self.log.emit(f"Serial open failed: {exc}", logging.ERROR)
            self.serial_state_changed.emit(False, "")

    @Slot()
    def close_port(self) -> None:
        try:
            self._sender.closeSerial()
        except Exception as exc:
            self.serial_error.emit(str(exc))
            self.log.emit(f"Serial close failed: {exc}", logging.ERROR)
        finally:
            self._keypress = None
            self._is_open = False
            self._port_label = ""

            self._gamepad_axis = (0.0, 0.0, 0.0, 0.0)
            self._gui_left = None
            self._gui_right = None
            self._last_stick_state = None

            self.serial_state_changed.emit(False, "")

    @Slot(str, bool)
    def write_row(self, row: str, is_show: bool = False) -> None:
        try:
            self._sender.writeRow(row, is_show=is_show)
        except Exception as exc:
            self.serial_error.emit(str(exc))
            self.log.emit(f"write_row failed: {exc}", logging.ERROR)

    @Slot(object, float, float, object)
    def on_keypress(
        self,
        buttons: object,
        duration: float = 0.1,
        wait: float = 0.1,
        input_type: object = None,
    ) -> None:
        if self._keypress is None:
            self.serial_error.emit("KeyPress is not initialized.")
            self.log.emit("KeyPress is not initialized.", logging.ERROR)
            return

        try:
            match input_type:
                case "press":
                    self._keypress.input(buttons)
                    self._cooperative_sleep(duration)
                    self._keypress.inputEnd(buttons)
                    self._cooperative_sleep(wait)
                case "press_w/o_wait":
                    self._keypress.input(buttons, overwrite=True)
                    self._cooperative_sleep(duration)
                case "hold":
                    self._keypress.hold(buttons)
                    self._cooperative_sleep(duration)
                case "hold end":
                    self._keypress.holdEnd(buttons)
                case "release":
                    self._keypress.inputEnd(buttons)
                case "release_all":
                    self._release_all_via_keypress()
                case _:
                    self.log.emit(
                        f"Unknown input_type in SerialWorker.on_keypress: {input_type}",
                        logging.ERROR,
                    )
        except Exception as exc:
            self.serial_error.emit(str(exc))
            self.log.emit(f"on_keypress failed: {exc}", logging.ERROR)

    @Slot(str)
    def on_named_button_pressed(self, name: str) -> None:
        btn = self._name_to_input(name)
        if btn is None or self._keypress is None:
            return
        try:
            self._keypress.hold(btn)
        except Exception as exc:
            self.serial_error.emit(str(exc))
            self.log.emit(f"on_named_button_pressed failed: {exc}", logging.ERROR)

    @Slot(str)
    def on_named_button_released(self, name: str) -> None:
        btn = self._name_to_input(name)
        if btn is None or self._keypress is None:
            return
        try:
            self._keypress.holdEnd(btn)
        except Exception as exc:
            self.serial_error.emit(str(exc))
            self.log.emit(f"on_named_button_released failed: {exc}", logging.ERROR)

    @Slot(float, float, float, float)
    def on_axis_moved(
        self,
        left_horizontal: float,
        left_vertical: float,
        right_horizontal: float,
        right_vertical: float,
    ) -> None:
        self._gamepad_axis = (
            float(left_horizontal),
            float(left_vertical),
            float(right_horizontal),
            float(right_vertical),
        )

    @Slot(str, float, float)
    def on_gui_stick_input(
        self, stick_name: str, angle_deg: float, radius: float
    ) -> None:
        radius = max(0.0, min(float(radius), 1.0))
        if stick_name == "LEFT":
            self._gui_left = (
                None if radius <= 0 else Direction(Stick.LEFT, angle_deg, radius)
            )
        elif stick_name == "RIGHT":
            self._gui_right = (
                None if radius <= 0 else Direction(Stick.RIGHT, angle_deg, radius)
            )
        self._apply_combined_sticks()

    @Slot()
    def _poll_latest_inputs(self) -> None:
        if self._keypress is None or not self._is_open:
            return

        # GUI stick の最新状態を pull
        if self._gui_stick_store is not None:
            left_gui, right_gui = self._gui_stick_store.snapshot()

            self._gui_left = (
                None
                if left_gui is None
                else Direction(Stick.LEFT, left_gui.angle, left_gui.radius)
            )
            self._gui_right = (
                None
                if right_gui is None
                else Direction(Stick.RIGHT, right_gui.angle, right_gui.radius)
            )

        left_h, left_v, right_h, right_v = self._gamepad_axis

        left_dir = (
            self._gui_left
            if self._gui_left is not None
            else self._axis_to_direction(Stick.LEFT, left_h, left_v)
        )
        right_dir = (
            self._gui_right
            if self._gui_right is not None
            else self._axis_to_direction(Stick.RIGHT, right_h, right_v)
        )

        state = (
            None if left_dir is None else (left_dir.x, left_dir.y),
            None if right_dir is None else (right_dir.x, right_dir.y),
        )

        if state == self._last_stick_state:
            return

        directions: list[Direction] = []
        if left_dir is not None:
            directions.append(left_dir)
        if right_dir is not None:
            directions.append(right_dir)

        try:
            self._keypress.input(directions, overwrite=True)
            self._last_stick_state = state
        except Exception as exc:
            self.serial_error.emit(str(exc))
            self.log.emit(f"_poll_latest_inputs failed: {exc}", logging.ERROR)

    def _apply_combined_sticks(self) -> None:
        if self._keypress is None:
            return

        left_h, left_v, right_h, right_v = self._gamepad_axis
        directions: list[Direction] = []

        left_dir = (
            self._gui_left
            if self._gui_left is not None
            else self._axis_to_direction(Stick.LEFT, left_h, left_v)
        )
        right_dir = (
            self._gui_right
            if self._gui_right is not None
            else self._axis_to_direction(Stick.RIGHT, right_h, right_v)
        )

        if left_dir is not None:
            directions.append(left_dir)
        if right_dir is not None:
            directions.append(right_dir)

        try:
            self._keypress.input(directions, overwrite=True)
        except Exception as exc:
            self.serial_error.emit(str(exc))
            self.log.emit(f"_apply_combined_sticks failed: {exc}", logging.ERROR)

    def _axis_to_direction(
        self,
        stick: Stick,
        horizontal: float,
        vertical: float,
    ) -> Optional[Direction]:
        r = math.sqrt(horizontal**2 + vertical**2)
        if r < self._dead_zone:
            return None

        normalized = (r - self._dead_zone) / (1.0 - self._dead_zone)
        normalized = max(0.0, min(normalized, 1.0))
        angle = -math.degrees(math.atan2(vertical, horizontal))
        return Direction(stick, angle, normalized)

    def _name_to_input(self, name: str) -> Optional[Button | Hat]:
        button_map = {
            "A": Button.A,
            "B": Button.B,
            "X": Button.X,
            "Y": Button.Y,
            "L": Button.L,
            "R": Button.R,
            "ZL": Button.ZL,
            "ZR": Button.ZR,
            "PLUS": Button.PLUS,
            "MINUS": Button.MINUS,
            "LCLICK": Button.LCLICK,
            "RCLICK": Button.RCLICK,
            "HOME": Button.HOME,
            "CAPTURE": Button.CAPTURE,
        }

        hat_map = {
            "TOP": Hat.TOP,
            "BTM": Hat.BTM,
            "LEFT": Hat.LEFT,
            "RIGHT": Hat.RIGHT,
        }

        if name in button_map:
            return button_map[name]
        if name in hat_map:
            return hat_map[name]
        return None

    def _release_all_via_keypress(self) -> None:
        if self._keypress is None:
            return
        fmt = getattr(self._keypress, "format", None)
        if fmt is None:
            return
        if hasattr(fmt, "resetAllButtons"):
            fmt.resetAllButtons()
        if hasattr(fmt, "unsetHat"):
            fmt.unsetHat()
        if hasattr(fmt, "resetAllDirections"):
            fmt.resetAllDirections()
        if hasattr(self._keypress, "input"):
            self._keypress.input([])

    @staticmethod
    def _cooperative_sleep(wait_seconds: float) -> None:
        wait_s = max(float(wait_seconds), 0.0)
        end = time.perf_counter() + wait_s

        busy_threshold = 0.002  # 最後の2msだけbusy wait

        while True:
            remain = end - time.perf_counter()
            if remain <= 0:
                return

            if remain > busy_threshold:
                time.sleep(max(remain - busy_threshold, 0.0))
            else:
                while time.perf_counter() < end:
                    pass
                return
