"""game_pad_connect.py

GamepadPoller + SettingWindow (key-config) implementation.

This file is intended to be the *single* source of truth for GamepadPoller.
MainWindow expects the following API to exist:
  - start(), stop(), reconnect(), set_paused(bool)
  - set_keymap(dict), set_use_lstick(bool), set_use_rstick(bool)
  - enumerate_devices() -> list[(index, name)]
  - select_device(index), select_device_by_name(name)
  - enable_nsw2_hid() -> bool
  - start_calibration() and signals calibration_progress/calibration_finished

Stick pipeline
--------------
- GamepadPoller produces pygame-standard axes where UP is negative.
- For NSw2 Pro Controller, optional smart calibration is applied via
  libs.nsw2_hid_enabler.NSw2StickCorrector.
- Deadzone is radial (not per-axis) to preserve diagonal intent.

"""

from __future__ import annotations

import logging
import math
import os
import sys
from functools import partial
from logging import DEBUG, NullHandler, getLogger
from typing import Dict, List, Optional, Tuple

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot

try:
    from libs.settings import Setting
except Exception:
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from libs.settings import Setting

from ui.key_config import Ui_Form

from libs.nsw2_hid_enabler import (
    NSw2StickCorrector,
    StickCalibrator,
    enable_hid,
    is_pyusb_available,
    get_nsw2_default_keymap,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════════

SWITCH_HATS: List[str] = ["TOP", "BTM", "LEFT", "RIGHT"]

POLL_INTERVAL_MS = 16
RECONNECT_INTERVAL_MS = 2000
STICK_DEADZONE = 0.15
TRIGGER_THRESHOLD = 0.5

WIDGET_MAP: List[Tuple[str, str, str, str, str]] = [
    ("button", "ZL", "lineEdit", "checkBox", "pushButton"),
    ("button", "L", "lineEdit_2", "checkBox_2", "pushButton_2"),
    ("button", "LCLICK", "lineEdit_3", "checkBox_3", "pushButton_3"),
    ("button", "MINUS", "lineEdit_4", "checkBox_4", "pushButton_4"),
    ("hat", "TOP", "lineEdit_5", "checkBox_5", "pushButton_5"),
    ("hat", "BTM", "lineEdit_6", "checkBox_6", "pushButton_6"),
    ("hat", "LEFT", "lineEdit_7", "checkBox_7", "pushButton_7"),
    ("hat", "RIGHT", "lineEdit_8", "checkBox_8", "pushButton_8"),
    ("button", "CAPTURE", "lineEdit_9", "checkBox_9", "pushButton_9"),
    ("button", "ZR", "lineEdit_10", "checkBox_10", "pushButton_10"),
    ("button", "R", "lineEdit_11", "checkBox_11", "pushButton_11"),
    ("button", "RCLICK", "lineEdit_12", "checkBox_12", "pushButton_12"),
    ("button", "PLUS", "lineEdit_13", "checkBox_13", "pushButton_13"),
    ("button", "A", "lineEdit_14", "checkBox_14", "pushButton_14"),
    ("button", "B", "lineEdit_15", "checkBox_15", "pushButton_15"),
    ("button", "X", "lineEdit_16", "checkBox_16", "pushButton_16"),
    ("button", "Y", "lineEdit_17", "checkBox_17", "pushButton_17"),
    ("button", "HOME", "lineEdit_18", "checkBox_18", "pushButton_18"),
]

DIRECTION_MAP: List[Tuple[str, str]] = [
    ("LStick", "checkBox_21"),
    ("RStick", "checkBox_22"),
]


# ═══════════════════════════════════════════════════════════════════════════
#  GamepadPoller
# ═══════════════════════════════════════════════════════════════════════════


class GamepadPoller(QObject):
    """Reads one gamepad via pygame in the current thread (QTimer)."""

    RAW_INPUT_LOG = False

    button_pressed = Signal(str)
    button_released = Signal(str)
    axis_changed = Signal(float, float, float, float)

    input_captured = Signal(str)

    device_connected = Signal(str)
    device_disconnected = Signal()

    calibration_progress = Signal(str)
    calibration_finished = Signal(dict)

    log = Signal(str, int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._logger = getLogger(f"{__name__}.GamepadPoller")
        self._logger.addHandler(NullHandler())
        self._logger.setLevel(DEBUG)
        self._logger.propagate = True

        self._joystick: Optional[pygame.joystick.Joystick] = None
        self._connected: bool = False
        self._target_index: Optional[int] = None

        self._poll_timer: Optional[QTimer] = None
        self._reconnect_timer: Optional[QTimer] = None

        self._keymap: Dict[str, str] = {}
        self._paused: bool = False
        self._use_lstick: bool = False
        self._use_rstick: bool = False
        self.deadzone: float = STICK_DEADZONE
        self.trigger_threshold: float = TRIGGER_THRESHOLD

        self._prev_buttons: Dict[str, bool] = {}
        self._prev_triggers: Dict[str, bool] = {}
        self._prev_hat: Dict[str, bool] = {d: False for d in SWITCH_HATS}

        self._capture_mode: bool = False

        self._stick_corrector: NSw2StickCorrector = NSw2StickCorrector()

        # calibration state: center -> yup -> ydown -> range
        self._calibrating: Optional[str] = None
        self._cal_left: Optional[StickCalibrator] = None
        self._cal_right: Optional[StickCalibrator] = None
        self._cal_frames: int = 0

        if not pygame.get_init():
            pygame.init()
        if not pygame.joystick.get_init():
            pygame.joystick.init()

    # ── properties ──────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── lifecycle ───────────────────────────────────────────────────

    @Slot()
    def start(self, interval_ms: int = POLL_INTERVAL_MS) -> None:
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._poll_timer.setInterval(interval_ms)
            self._poll_timer.timeout.connect(self._poll)

        if self._reconnect_timer is None:
            self._reconnect_timer = QTimer(self)
            self._reconnect_timer.setInterval(RECONNECT_INTERVAL_MS)
            self._reconnect_timer.timeout.connect(self._try_connect)

        self._try_connect()
        self._poll_timer.start()
        self._reconnect_timer.start()
        self._emit_log(logging.INFO, "GamepadPoller started")

    @Slot()
    def stop(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
        if self._reconnect_timer is not None:
            self._reconnect_timer.stop()
        self._emit_log(logging.INFO, "GamepadPoller stopped")

    # ── configuration ───────────────────────────────────────────────

    @Slot(dict)
    def set_keymap(self, keymap: Dict[str, str]) -> None:
        self._keymap = dict(keymap)
        self._clear_state()

    @Slot(bool)
    def set_use_lstick(self, enabled: bool) -> None:
        self._use_lstick = bool(enabled)

    @Slot(bool)
    def set_use_rstick(self, enabled: bool) -> None:
        self._use_rstick = bool(enabled)

    @Slot(bool)
    def set_paused(self, paused: bool) -> None:
        self._paused = bool(paused)

    def set_stick_corrector(self, corrector: NSw2StickCorrector) -> None:
        self._stick_corrector = corrector

    # ── capture ─────────────────────────────────────────────────────

    @Slot()
    def start_capture(self) -> None:
        self._capture_mode = True

    @Slot()
    def cancel_capture(self) -> None:
        self._capture_mode = False

    # ── device enumeration & selection ──────────────────────────────

    def _drop_current_device(self) -> None:
        """Safely drop the current pygame Joystick handle.

        This prevents `pygame.error: Joystick not initialized` when the
        joystick subsystem is reinitialized (quit/init) during manual
        device enumeration or switching while polling is active.
        """
        if self._joystick is not None or self._connected:
            self._joystick = None
            self._connected = False
            self._clear_state()
            try:
                self.device_disconnected.emit()
            except Exception:
                pass

    def enumerate_devices(self) -> list[tuple[int, str]]:
        """Return list of (index, name) for currently available joysticks.

        NOTE: We refresh the pygame joystick subsystem here. Because that
        invalidates existing Joystick objects, we first drop the current
        handle to prevent poll-time errors.
        """
        self._drop_current_device()
        pygame.joystick.quit()
        pygame.joystick.init()
        out: list[tuple[int, str]] = []
        for i in range(pygame.joystick.get_count()):
            try:
                js = pygame.joystick.Joystick(i)
                js.init()
                out.append((i, js.get_name()))
            except Exception:
                continue
        return out

    def select_device(self, index: int) -> bool:
        """Select device by index and reconnect immediately."""
        try:
            idx = int(index)
        except Exception:
            return False
        if idx < 0:
            return False
        self._target_index = idx
        self.reconnect()
        return True

    def select_device_by_name(self, name: str) -> bool:
        """Select device by exact name match and reconnect immediately."""
        try:
            devices = self.enumerate_devices()
            for idx, dev_name in devices:
                if dev_name == name:
                    self._target_index = idx
                    self.reconnect()
                    return True
        except Exception:
            return False
        return False

    @Slot()
    def reconnect(self) -> None:
        if self._connected:
            self._joystick = None
            self._connected = False
            self._clear_state()
            self.device_disconnected.emit()
        self._try_connect()

    def _try_connect(self) -> None:
        if self._connected:
            return
        # Drop any stale handle before reinitializing joystick subsystem
        self._joystick = None
        self._connected = False
        pygame.joystick.quit()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        if count <= 0:
            return
        idx = self._target_index if self._target_index is not None else 0
        if idx >= count:
            idx = 0
        try:
            js = pygame.joystick.Joystick(idx)
            js.init()
            self._joystick = js
            self._connected = True
            self._clear_state()
            self.device_connected.emit(js.get_name())
            self._emit_log(
                logging.INFO, f"Connected: {js.get_name()} (device {idx}/{count})"
            )
        except Exception as exc:
            self._joystick = None
            self._connected = False
            self._emit_log(logging.ERROR, f"Connection failed: {exc}")

    def _on_disconnect(self) -> None:
        self._joystick = None
        self._connected = False
        self._clear_state()
        self.device_disconnected.emit()
        self._emit_log(logging.WARNING, "Device disconnected")

    # ── NSw2 HID enable ─────────────────────────────────────────────

    @Slot()
    def enable_nsw2_hid(self) -> bool:
        if not is_pyusb_available():
            self._emit_log(
                logging.WARNING,
                "pyusb/libusb not available: pip install pyusb libusb-package",
            )
            return False
        res = enable_hid(player_number=1)
        self._emit_log(
            logging.INFO if res.success else logging.ERROR, f"NSw2 HID: {res.message}"
        )
        if res.success:
            # start with identity corrector; user can calibrate or load saved profile
            self._stick_corrector = NSw2StickCorrector.default_nsw2()
        return res.success

    # ── calibration ────────────────────────────────────────────────

    @Slot()
    def start_calibration(self) -> None:
        """Smart calibration: center(2s) -> up(1s) -> down(1s) -> swirl(3s)."""
        self._cal_left = StickCalibrator()
        self._cal_right = StickCalibrator()
        self._cal_frames = 0
        self._calibrating = "center"
        self.calibration_progress.emit(
            "【1/4】スティックから手を放してください... (2秒)"
        )

    def _poll_calibration(self) -> None:
        js = self._joystick
        if js is None or self._cal_left is None or self._cal_right is None:
            self._calibrating = None
            return

        lx, ly = js.get_axis(0), js.get_axis(1)
        rx, ry = js.get_axis(2), js.get_axis(3)
        self._cal_frames += 1

        if self._calibrating == "center":
            self._cal_left.record_center(lx, ly)
            self._cal_right.record_center(rx, ry)
            if self._cal_frames >= 120:
                self._cal_frames = 0
                self._calibrating = "yup"
                self.calibration_progress.emit(
                    "【2/4】両スティックを『上』に倒して保持してください... (1秒)"
                )

        elif self._calibrating == "yup":
            self._cal_left.record_y_up(ly)
            self._cal_right.record_y_up(ry)
            if self._cal_frames >= 60:
                self._cal_frames = 0
                self._calibrating = "ydown"
                self.calibration_progress.emit(
                    "【3/4】両スティックを『下』に倒して保持してください... (1秒)"
                )

        elif self._calibrating == "ydown":
            self._cal_left.record_y_down(ly)
            self._cal_right.record_y_down(ry)
            if self._cal_frames >= 60:
                self._cal_frames = 0
                self._calibrating = "range"
                self.calibration_progress.emit(
                    "【4/4】両スティックを全方向にグリグリ回してください... (3秒)"
                )

        elif self._calibrating == "range":
            self._cal_left.record_range(lx, ly)
            self._cal_right.record_range(rx, ry)
            if self._cal_frames >= 190:
                self._finish_calibration()

    def _finish_calibration(self) -> None:
        assert self._cal_left is not None and self._cal_right is not None
        left_prof = self._cal_left.build_profile()
        right_prof = self._cal_right.build_profile()
        self._stick_corrector = NSw2StickCorrector(
            enabled=True, left=left_prof, right=right_prof
        )
        payload = self._stick_corrector.to_dict()

        msg = (
            "キャリブレーション完了!\n"
            f"  L center=({left_prof.center_x:+.3f},{left_prof.center_y:+.3f}) invert_y={left_prof.invert_y}\n"
            f"  R center=({right_prof.center_x:+.3f},{right_prof.center_y:+.3f}) invert_y={right_prof.invert_y}"
        )
        self._emit_log(logging.INFO, msg)
        self.calibration_progress.emit(msg)
        self.calibration_finished.emit(payload)

        self._calibrating = None
        self._cal_left = None
        self._cal_right = None
        self._cal_frames = 0

    # ── helpers ────────────────────────────────────────────────────

    def _clear_state(self) -> None:
        self._prev_buttons.clear()
        self._prev_triggers.clear()
        self._prev_hat = {d: False for d in SWITCH_HATS}

    def _emit_log(self, level: int, msg: str) -> None:
        self._logger.log(level, msg)
        self.log.emit(msg, level)

    def _apply_deadzone_radial(self, x: float, y: float) -> tuple[float, float]:
        r = math.sqrt(x * x + y * y)
        if r < self.deadzone:
            return 0.0, 0.0
        scaled = (r - self.deadzone) / (1.0 - self.deadzone)
        scaled = min(scaled, 1.0)
        ratio = scaled / r
        return x * ratio, y * ratio

    @Slot()
    def _poll(self) -> None:
        if self._paused or not self._connected or self._joystick is None:
            return

        # calibration has priority
        if self._calibrating is not None:
            pygame.event.pump()
            self._poll_calibration()
            return

        events = pygame.event.get()

        if self._capture_mode:
            self._process_capture(events)
            return

        for ev in events:
            if ev.type == pygame.JOYBUTTONDOWN:
                if self.RAW_INPUT_LOG:
                    self._emit_log(logging.DEBUG, f"[RAW] BUTTON DOWN: {ev.button}")
                self._handle_button(ev.button, True)
            elif ev.type == pygame.JOYBUTTONUP:
                if self.RAW_INPUT_LOG:
                    self._emit_log(logging.DEBUG, f"[RAW] BUTTON UP:   {ev.button}")
                self._handle_button(ev.button, False)
            elif ev.type == pygame.JOYHATMOTION:
                self._handle_hat(ev.value)
            elif ev.type == pygame.JOYDEVICEREMOVED:
                self._on_disconnect()
                return

        self._poll_sticks()
        self._poll_triggers()

    def _process_capture(self, events: list) -> None:
        for ev in events:
            key: Optional[str] = None
            if ev.type == pygame.JOYBUTTONDOWN:
                key = f"button.{ev.button}"
            elif ev.type == pygame.JOYAXISMOTION:
                if ev.axis in (4, 5) and abs(ev.value) > self.trigger_threshold:
                    key = f"axis.{ev.axis}"
            elif ev.type == pygame.JOYHATMOTION:
                key = self._hat_value_to_key(ev.value)
            elif ev.type == pygame.JOYDEVICEREMOVED:
                self._on_disconnect()
                self._capture_mode = False
                return
            if key is not None:
                self._capture_mode = False
                self.input_captured.emit(key)
                return

    @staticmethod
    def _hat_value_to_key(value: Tuple[int, int]) -> Optional[str]:
        hx, hy = value
        if hy > 0:
            return "hat.TOP"
        if hy < 0:
            return "hat.BTM"
        if hx < 0:
            return "hat.LEFT"
        if hx > 0:
            return "hat.RIGHT"
        return None

    def _handle_button(self, index: int, pressed: bool) -> None:
        key = f"button.{index}"
        name = self._keymap.get(key)
        if name is None:
            return
        prev = self._prev_buttons.get(key, False)
        if prev == pressed:
            return
        self._prev_buttons[key] = pressed
        if pressed:
            self.button_pressed.emit(name)
        else:
            self.button_released.emit(name)

    def _handle_hat(self, value: Tuple[int, int]) -> None:
        hx, hy = value
        current = {
            "TOP": hy > 0,
            "BTM": hy < 0,
            "LEFT": hx < 0,
            "RIGHT": hx > 0,
        }
        for direction, active in current.items():
            key = f"hat.{direction}"
            name = self._keymap.get(key)
            if name is None:
                continue
            prev = self._prev_hat.get(direction, False)
            if prev == active:
                continue
            self._prev_hat[direction] = active
            if active:
                self.button_pressed.emit(name)
            else:
                self.button_released.emit(name)

    def _poll_sticks(self) -> None:
        js = self._joystick
        if js is None:
            return

        try:
            raw_lx, raw_ly = js.get_axis(0), js.get_axis(1)
            raw_rx, raw_ry = js.get_axis(2), js.get_axis(3)
        except pygame.error as exc:
            # Joystick handle may be invalidated by pygame.joystick.quit()/init()
            self._emit_log(logging.WARNING, f"Joystick read failed: {exc}")
            self._on_disconnect()
            return

        # apply smart correction (also normalizes y sign to pygame standard)
        cor_lx, cor_ly = self._stick_corrector.correct_left(raw_lx, raw_ly)
        cor_rx, cor_ry = self._stick_corrector.correct_right(raw_rx, raw_ry)

        if self.RAW_INPUT_LOG:
            self._emit_log(
                logging.DEBUG,
                f"[RAW] STICK L:({raw_lx:+.3f},{raw_ly:+.3f}) R:({raw_rx:+.3f},{raw_ry:+.3f}) -> "
                f"COR L:({cor_lx:+.3f},{cor_ly:+.3f}) R:({cor_rx:+.3f},{cor_ry:+.3f})",
            )

        if self._use_lstick:
            lx, ly = self._apply_deadzone_radial(cor_lx, cor_ly)
        else:
            lx, ly = 0.0, 0.0

        if self._use_rstick:
            rx, ry = self._apply_deadzone_radial(cor_rx, cor_ry)
        else:
            rx, ry = 0.0, 0.0

        self.axis_changed.emit(lx, ly, rx, ry)

    def _poll_triggers(self) -> None:
        js = self._joystick
        if js is None:
            return
        for axis_idx in (4, 5):
            key = f"axis.{axis_idx}"
            name = self._keymap.get(key)
            if name is None:
                continue
            try:
                value = js.get_axis(axis_idx)
            except Exception:
                continue
            pressed = value >= self.trigger_threshold
            prev = self._prev_triggers.get(key, False)
            if prev == pressed:
                continue
            self._prev_triggers[key] = pressed
            if pressed:
                self.button_pressed.emit(name)
            else:
                self.button_released.emit(name)


# ═══════════════════════════════════════════════════════════════════════════
#  SettingWindow (key config)
# ═══════════════════════════════════════════════════════════════════════════


class SettingWindow(QtWidgets.QWidget, Ui_Form):
    """Key-config UI (uses shared GamepadPoller)."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        _setting: Setting | None = None,
        poller: GamepadPoller | None = None,
    ) -> None:
        super().__init__(parent)
        self.setupUi(self)

        self.setting: Setting = _setting
        self.setting.load()
        self._js: dict = self.setting.setting["key_config"]["joystick"]

        self._capture_target: Optional[str] = None

        if poller is not None:
            self.poller = poller
            self._owns_poller = False
        else:
            self.poller = GamepadPoller(self)
            self._owns_poller = True

        self.poller.input_captured.connect(self._on_input_captured)
        self.poller.device_connected.connect(lambda name: self.setWindowTitle(name))

        self._load_config_to_ui()
        self._connect_widgets()

        self.pushButton_19.clicked.connect(self._apply_keymap)

        if self._owns_poller:
            self.poller.start()
        self._apply_keymap()

    def _load_config_to_ui(self) -> None:
        for section, key, le_attr, cb_attr, _ in WIDGET_MAP:
            cfg = self._js[section][key]
            le: QtWidgets.QLineEdit = getattr(self, le_attr)
            cb: QtWidgets.QCheckBox = getattr(self, cb_attr)
            le.blockSignals(True)
            le.setText(cfg.get("assign", ""))
            le.blockSignals(False)
            cb.blockSignals(True)
            cb.setChecked(cfg.get("state", False))
            cb.blockSignals(False)

        for dir_key, cb_attr in DIRECTION_MAP:
            cb: QtWidgets.QCheckBox = getattr(self, cb_attr)
            cb.blockSignals(True)
            cb.setChecked(self._js["direction"].get(dir_key, False))
            cb.blockSignals(False)

    def _save_entry(
        self, section: str, key: str, le_attr: str, cb_attr: str, *_args
    ) -> None:
        le: QtWidgets.QLineEdit = getattr(self, le_attr)
        cb: QtWidgets.QCheckBox = getattr(self, cb_attr)
        self._js[section][key] = {"state": cb.isChecked(), "assign": le.text()}

    def _save_direction(self, dir_key: str, cb_attr: str, *_args) -> None:
        cb: QtWidgets.QCheckBox = getattr(self, cb_attr)
        self._js["direction"][dir_key] = cb.isChecked()

    def _connect_widgets(self) -> None:
        for section, key, le_attr, cb_attr, pb_attr in WIDGET_MAP:
            le: QtWidgets.QLineEdit = getattr(self, le_attr)
            cb: QtWidgets.QCheckBox = getattr(self, cb_attr)
            pb: QtWidgets.QPushButton = getattr(self, pb_attr)
            save_fn = partial(self._save_entry, section, key, le_attr, cb_attr)
            le.textChanged.connect(save_fn)
            cb.stateChanged.connect(save_fn)
            pb.clicked.connect(partial(self._on_set_clicked, le_attr))

        for dir_key, cb_attr in DIRECTION_MAP:
            cb: QtWidgets.QCheckBox = getattr(self, cb_attr)
            cb.stateChanged.connect(partial(self._save_direction, dir_key, cb_attr))

    def _on_set_clicked(self, le_attr: str, *_args) -> None:
        self._capture_target = le_attr
        self.poller.start_capture()

    @Slot(str)
    def _on_input_captured(self, physical_key: str) -> None:
        if self._capture_target is None:
            return
        le: QtWidgets.QLineEdit = getattr(self, self._capture_target)
        le.setText(physical_key)
        self._capture_target = None

    def _build_keymap(self) -> Dict[str, str]:
        km: Dict[str, str] = {}
        for section in ("button", "hat"):
            for name, cfg in self._js[section].items():
                if cfg.get("state") and cfg.get("assign"):
                    km[cfg["assign"]] = name
        return km

    @Slot()
    def _apply_keymap(self) -> None:
        self.poller.set_keymap(self._build_keymap())
        self.poller.set_use_lstick(self._js["direction"].get("LStick", False))
        self.poller.set_use_rstick(self._js["direction"].get("RStick", False))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.setting.save()
        if self._owns_poller:
            self.poller.stop()
        super().closeEvent(event)
