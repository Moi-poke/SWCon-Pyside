from __future__ import annotations

import logging
import os
import sys
from logging import DEBUG, NullHandler, getLogger
from typing import Optional

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
import pygame.locals
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QObject, QTimer, Signal, Slot

try:
    from libs.settings import Setting
except Exception:
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from libs.settings import Setting

from ui.key_config import Ui_Form


class SettingWindow(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None, _setting=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setting = _setting
        self.setting.load()
        self.controller_setting = self.setting.setting["key_config"]["joystick"]

        self.set_config()
        self.set_state()
        self.connect_function()

        pygame.init()
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            self.setWindowTitle(self.joystick.get_name())

        self.keymap = {
            v["assign"]: k
            for k, v in self.setting.setting["key_config"]["joystick"]["button"].items()
            if v["state"]
        } | {
            v["assign"]: k
            for k, v in self.setting.setting["key_config"]["joystick"]["hat"].items()
            if v["state"]
        }

        self.Controller_worker = GamepadController()
        self.Controller_thread = QtCore.QThread(self)
        self.Controller_worker.moveToThread(self.Controller_thread)
        self.Controller_thread.started.connect(self.Controller_worker.run)
        self.Controller_worker.set_keymap(self.keymap)
        self.Controller_thread.start()

    def connect_function(self) -> None:
        self.lineEdit.textChanged.connect(self.btn_ZL)
        self.lineEdit_2.textChanged.connect(self.btn_L)
        self.lineEdit_3.textChanged.connect(self.btn_LCLICK)
        self.lineEdit_4.textChanged.connect(self.btn_MINUS)
        self.lineEdit_5.textChanged.connect(self.hat_TOP)
        self.lineEdit_6.textChanged.connect(self.hat_BTM)
        self.lineEdit_7.textChanged.connect(self.hat_LEFT)
        self.lineEdit_8.textChanged.connect(self.hat_RIGHT)
        self.lineEdit_9.textChanged.connect(self.btn_CAPTURE)
        self.lineEdit_10.textChanged.connect(self.btn_ZR)
        self.lineEdit_11.textChanged.connect(self.btn_R)
        self.lineEdit_12.textChanged.connect(self.btn_RCLICK)
        self.lineEdit_13.textChanged.connect(self.btn_PLUS)
        self.lineEdit_14.textChanged.connect(self.btn_A)
        self.lineEdit_15.textChanged.connect(self.btn_B)
        self.lineEdit_16.textChanged.connect(self.btn_X)
        self.lineEdit_17.textChanged.connect(self.btn_Y)
        self.lineEdit_18.textChanged.connect(self.btn_HOME)

        self.checkBox.stateChanged.connect(self.btn_ZL)
        self.checkBox_2.stateChanged.connect(self.btn_L)
        self.checkBox_3.stateChanged.connect(self.btn_LCLICK)
        self.checkBox_4.stateChanged.connect(self.btn_MINUS)
        self.checkBox_5.stateChanged.connect(self.hat_TOP)
        self.checkBox_6.stateChanged.connect(self.hat_BTM)
        self.checkBox_7.stateChanged.connect(self.hat_LEFT)
        self.checkBox_8.stateChanged.connect(self.hat_RIGHT)
        self.checkBox_9.stateChanged.connect(self.btn_CAPTURE)
        self.checkBox_10.stateChanged.connect(self.btn_ZR)
        self.checkBox_11.stateChanged.connect(self.btn_R)
        self.checkBox_12.stateChanged.connect(self.btn_RCLICK)
        self.checkBox_13.stateChanged.connect(self.btn_PLUS)
        self.checkBox_14.stateChanged.connect(self.btn_A)
        self.checkBox_15.stateChanged.connect(self.btn_B)
        self.checkBox_16.stateChanged.connect(self.btn_X)
        self.checkBox_17.stateChanged.connect(self.btn_Y)
        self.checkBox_18.stateChanged.connect(self.btn_HOME)
        self.checkBox_21.stateChanged.connect(self.dir_L)
        self.checkBox_22.stateChanged.connect(self.dir_R)

        self.pushButton.clicked.connect(self.set_btn_ZL)
        self.pushButton_2.clicked.connect(self.set_btn_L)
        self.pushButton_3.clicked.connect(self.set_btn_LCLICK)
        self.pushButton_4.clicked.connect(self.set_btn_MINUS)
        self.pushButton_5.clicked.connect(self.set_hat_TOP)
        self.pushButton_6.clicked.connect(self.set_hat_BTM)
        self.pushButton_7.clicked.connect(self.set_hat_LEFT)
        self.pushButton_8.clicked.connect(self.set_hat_RIGHT)
        self.pushButton_9.clicked.connect(self.set_btn_CAPTURE)
        self.pushButton_10.clicked.connect(self.set_btn_ZR)
        self.pushButton_11.clicked.connect(self.set_btn_R)
        self.pushButton_12.clicked.connect(self.set_btn_RCLICK)
        self.pushButton_13.clicked.connect(self.set_btn_PLUS)
        self.pushButton_14.clicked.connect(self.set_btn_A)
        self.pushButton_15.clicked.connect(self.set_btn_B)
        self.pushButton_16.clicked.connect(self.set_btn_X)
        self.pushButton_17.clicked.connect(self.set_btn_Y)
        self.pushButton_18.clicked.connect(self.set_btn_HOME)
        self.pushButton_19.clicked.connect(self.remap_key)

    def set_config(self) -> None:
        self.lineEdit.setText(self.controller_setting["button"]["ZL"]["assign"])
        self.lineEdit_2.setText(self.controller_setting["button"]["L"]["assign"])
        self.lineEdit_3.setText(self.controller_setting["button"]["LCLICK"]["assign"])
        self.lineEdit_4.setText(self.controller_setting["button"]["MINUS"]["assign"])
        self.lineEdit_5.setText(self.controller_setting["hat"]["TOP"]["assign"])
        self.lineEdit_6.setText(self.controller_setting["hat"]["BTM"]["assign"])
        self.lineEdit_7.setText(self.controller_setting["hat"]["LEFT"]["assign"])
        self.lineEdit_8.setText(self.controller_setting["hat"]["RIGHT"]["assign"])
        self.lineEdit_9.setText(self.controller_setting["button"]["CAPTURE"]["assign"])
        self.lineEdit_10.setText(self.controller_setting["button"]["ZR"]["assign"])
        self.lineEdit_11.setText(self.controller_setting["button"]["R"]["assign"])
        self.lineEdit_12.setText(self.controller_setting["button"]["RCLICK"]["assign"])
        self.lineEdit_13.setText(self.controller_setting["button"]["PLUS"]["assign"])
        self.lineEdit_14.setText(self.controller_setting["button"]["A"]["assign"])
        self.lineEdit_15.setText(self.controller_setting["button"]["B"]["assign"])
        self.lineEdit_16.setText(self.controller_setting["button"]["X"]["assign"])
        self.lineEdit_17.setText(self.controller_setting["button"]["Y"]["assign"])
        self.lineEdit_18.setText(self.controller_setting["button"]["HOME"]["assign"])

    def set_state(self) -> None:
        if self.controller_setting["button"]["ZL"]["state"]:
            self.checkBox.toggle()
        if self.controller_setting["button"]["L"]["state"]:
            self.checkBox_2.toggle()
        if self.controller_setting["button"]["LCLICK"]["state"]:
            self.checkBox_3.toggle()
        if self.controller_setting["button"]["MINUS"]["state"]:
            self.checkBox_4.toggle()
        if self.controller_setting["hat"]["TOP"]["state"]:
            self.checkBox_5.toggle()
        if self.controller_setting["hat"]["BTM"]["state"]:
            self.checkBox_6.toggle()
        if self.controller_setting["hat"]["LEFT"]["state"]:
            self.checkBox_7.toggle()
        if self.controller_setting["hat"]["RIGHT"]["state"]:
            self.checkBox_8.toggle()
        if self.controller_setting["button"]["CAPTURE"]["state"]:
            self.checkBox_9.toggle()
        if self.controller_setting["button"]["ZR"]["state"]:
            self.checkBox_10.toggle()
        if self.controller_setting["button"]["R"]["state"]:
            self.checkBox_11.toggle()
        if self.controller_setting["button"]["RCLICK"]["state"]:
            self.checkBox_12.toggle()
        if self.controller_setting["button"]["PLUS"]["state"]:
            self.checkBox_13.toggle()
        if self.controller_setting["button"]["A"]["state"]:
            self.checkBox_14.toggle()
        if self.controller_setting["button"]["B"]["state"]:
            self.checkBox_15.toggle()
        if self.controller_setting["button"]["X"]["state"]:
            self.checkBox_16.toggle()
        if self.controller_setting["button"]["Y"]["state"]:
            self.checkBox_17.toggle()
        if self.controller_setting["button"]["HOME"]["state"]:
            self.checkBox_18.toggle()
        if self.controller_setting["direction"]["LStick"]:
            self.checkBox_21.toggle()
        if self.controller_setting["direction"]["RStick"]:
            self.checkBox_22.toggle()

    def remap_key(self) -> None:
        self.keymap = {
            v["assign"]: k
            for k, v in self.setting.setting["key_config"]["joystick"]["button"].items()
            if v["state"]
        } | {
            v["assign"]: k
            for k, v in self.setting.setting["key_config"]["joystick"]["hat"].items()
            if v["state"]
        }
        self.Controller_worker.set_keymap(self.keymap)

    def btn_ZL(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["ZL"] = {
            "state": self.checkBox.isChecked(),
            "assign": self.lineEdit.text(),
        }

    def btn_L(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["L"] = {
            "state": self.checkBox_2.isChecked(),
            "assign": self.lineEdit_2.text(),
        }

    def btn_LCLICK(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["LCLICK"] = {
            "state": self.checkBox_3.isChecked(),
            "assign": self.lineEdit_3.text(),
        }

    def btn_MINUS(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["MINUS"] = {
            "state": self.checkBox_4.isChecked(),
            "assign": self.lineEdit_4.text(),
        }

    def hat_TOP(self) -> None:
        self.setting.setting["key_config"]["joystick"]["hat"]["TOP"] = {
            "state": self.checkBox_5.isChecked(),
            "assign": self.lineEdit_5.text(),
        }

    def hat_BTM(self) -> None:
        self.setting.setting["key_config"]["joystick"]["hat"]["BTM"] = {
            "state": self.checkBox_6.isChecked(),
            "assign": self.lineEdit_6.text(),
        }

    def hat_LEFT(self) -> None:
        self.setting.setting["key_config"]["joystick"]["hat"]["LEFT"] = {
            "state": self.checkBox_7.isChecked(),
            "assign": self.lineEdit_7.text(),
        }

    def hat_RIGHT(self) -> None:
        self.setting.setting["key_config"]["joystick"]["hat"]["RIGHT"] = {
            "state": self.checkBox_8.isChecked(),
            "assign": self.lineEdit_8.text(),
        }

    def btn_CAPTURE(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["CAPTURE"] = {
            "state": self.checkBox_9.isChecked(),
            "assign": self.lineEdit_9.text(),
        }

    def btn_ZR(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["ZR"] = {
            "state": self.checkBox_10.isChecked(),
            "assign": self.lineEdit_10.text(),
        }

    def btn_R(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["R"] = {
            "state": self.checkBox_11.isChecked(),
            "assign": self.lineEdit_11.text(),
        }

    def btn_RCLICK(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["RCLICK"] = {
            "state": self.checkBox_12.isChecked(),
            "assign": self.lineEdit_12.text(),
        }

    def btn_PLUS(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["PLUS"] = {
            "state": self.checkBox_13.isChecked(),
            "assign": self.lineEdit_13.text(),
        }

    def btn_A(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["A"] = {
            "state": self.checkBox_14.isChecked(),
            "assign": self.lineEdit_14.text(),
        }

    def btn_B(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["B"] = {
            "state": self.checkBox_15.isChecked(),
            "assign": self.lineEdit_15.text(),
        }

    def btn_X(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["X"] = {
            "state": self.checkBox_16.isChecked(),
            "assign": self.lineEdit_16.text(),
        }

    def btn_Y(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["Y"] = {
            "state": self.checkBox_17.isChecked(),
            "assign": self.lineEdit_17.text(),
        }

    def btn_HOME(self) -> None:
        self.setting.setting["key_config"]["joystick"]["button"]["HOME"] = {
            "state": self.checkBox_18.isChecked(),
            "assign": self.lineEdit_18.text(),
        }

    def dir_L(self) -> None:
        self.setting.setting["key_config"]["joystick"]["direction"]["LStick"] = (
            self.checkBox_21.isChecked()
        )

    def dir_R(self) -> None:
        self.setting.setting["key_config"]["joystick"]["direction"]["RStick"] = (
            self.checkBox_22.isChecked()
        )

    def _set_line_edit_from_key(self, widget) -> None:
        ret = self.set_key()
        widget.setText(str(ret))

    def set_btn_ZL(self) -> None:
        self._set_line_edit_from_key(self.lineEdit)

    def set_btn_L(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_2)

    def set_btn_LCLICK(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_3)

    def set_btn_MINUS(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_4)

    def set_hat_TOP(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_5)

    def set_hat_BTM(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_6)

    def set_hat_LEFT(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_7)

    def set_hat_RIGHT(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_8)

    def set_btn_CAPTURE(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_9)

    def set_btn_ZR(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_10)

    def set_btn_R(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_11)

    def set_btn_RCLICK(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_12)

    def set_btn_PLUS(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_13)

    def set_btn_A(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_14)

    def set_btn_B(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_15)

    def set_btn_X(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_16)

    def set_btn_Y(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_17)

    def set_btn_HOME(self) -> None:
        self._set_line_edit_from_key(self.lineEdit_18)

    @staticmethod
    def set_key():
        ret = None
        while True:
            for e in pygame.event.get():
                if e.type == pygame.locals.JOYAXISMOTION:
                    if e.axis in (4, 5):
                        ret = f"axis.{e.axis}"
                elif e.type == pygame.locals.JOYHATMOTION:
                    ret = e
                elif e.type == pygame.locals.JOYBUTTONDOWN:
                    ret = f"button.{e.button}"

                if ret is not None:
                    return ret

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.setting.save()
        if self.Controller_worker is not None:
            self.Controller_worker.stop()
        if self.Controller_thread is not None:
            self.Controller_thread.quit()
            self.Controller_thread.wait(2000)
        return super().closeEvent(a0)


class GamepadController(QObject):
    ZL_PRESSED = Signal()
    L_PRESSED = Signal()
    LCLICK_PRESSED = Signal()
    MINUS_PRESSED = Signal()
    TOP_PRESSED = Signal()
    BTM_PRESSED = Signal()
    LEFT_PRESSED = Signal()
    RIGHT_PRESSED = Signal()
    CAPTURE_PRESSED = Signal()
    ZR_PRESSED = Signal()
    R_PRESSED = Signal()
    RCLICK_PRESSED = Signal()
    PLUS_PRESSED = Signal()
    A_PRESSED = Signal()
    B_PRESSED = Signal()
    X_PRESSED = Signal()
    Y_PRESSED = Signal()
    HOME_PRESSED = Signal()

    ZL_RELEASED = Signal()
    L_RELEASED = Signal()
    LCLICK_RELEASED = Signal()
    MINUS_RELEASED = Signal()
    TOP_RELEASED = Signal()
    BTM_RELEASED = Signal()
    LEFT_RELEASED = Signal()
    RIGHT_RELEASED = Signal()
    CAPTURE_RELEASED = Signal()
    ZR_RELEASED = Signal()
    R_RELEASED = Signal()
    RCLICK_RELEASED = Signal()
    PLUS_RELEASED = Signal()
    A_RELEASED = Signal()
    B_RELEASED = Signal()
    X_RELEASED = Signal()
    Y_RELEASED = Signal()
    HOME_RELEASED = Signal()

    AXIS_MOVED = Signal(float, float, float, float)

    button_pressed = Signal(str)
    button_released = Signal(str)
    axis_moved = Signal(float, float, float, float)
    print_strings = Signal(str, int)
    log = Signal(str, int)

    def __init__(self) -> None:
        super().__init__()

        self.logger = getLogger(__name__)
        self.logger.addHandler(NullHandler())
        self.logger.setLevel(DEBUG)
        self.logger.propagate = True

        self.joystick_: Optional[pygame.joystick.Joystick] = None
        self.use_Rstick = False
        self.use_Lstick = False
        self.is_alive = True
        self.keymap: dict[str, str] = {}
        self.pause = False
        self.isCanceled = False
        self.no_joystick = True

        self._prev_button_state: dict[str, bool] = {}
        self._prev_axis_button_state: dict[str, int] = {}
        self._prev_hat_state: dict[str, bool] = {}
        self._timer: Optional[QTimer] = None

        pygame.init()
        pygame.joystick.init()
        self.connect_joystick()

    def _emit_log(self, level: int, s: str, force: bool = False) -> None:
        if force or not self.isCanceled:
            msg = f"{s}"
            self.print_strings.emit(msg, level)
            self.log.emit(msg, level)

    def debug(self, s, force: bool = False) -> None:
        self._emit_log(logging.DEBUG, str(s), force=force)

    def info(self, s, force: bool = False) -> None:
        self._emit_log(logging.INFO, str(s), force=force)

    def warning(self, s, force: bool = False) -> None:
        self._emit_log(logging.WARNING, str(s), force=force)

    def error(self, s, force: bool = False) -> None:
        self._emit_log(logging.ERROR, str(s), force=force)

    def critical(self, s, force: bool = False) -> None:
        self._emit_log(logging.CRITICAL, str(s), force=force)

    @Slot()
    def connect_joystick(self) -> None:
        self.debug("Connecting Joystick...")
        try:
            pygame.joystick.quit()
            pygame.joystick.init()

            if pygame.joystick.get_count() <= 0:
                self.no_joystick = True
                self.joystick_ = None
                self.debug("Connection failed: no joystick")
                return

            self.joystick_ = pygame.joystick.Joystick(0)
            self.joystick_.init()
            self.no_joystick = False

            # 追加: stateをクリア
            self._prev_button_state.clear()
            self._prev_axis_button_state.clear()
            self._prev_hat_state.clear()

            self.debug("Successfully connected")
        except Exception as exc:
            self.no_joystick = True
            self.joystick_ = None
            self.debug(f"Connection failed: {exc}")

    @Slot(dict)
    def set_keymap(self, keymap: dict[str, str]) -> None:
        self.keymap = dict(keymap)

    @Slot(bool)
    def set_l_stick(self, v: bool) -> None:
        self.use_Lstick = bool(v)

    @Slot(bool)
    def set_r_stick(self, v: bool) -> None:
        self.use_Rstick = bool(v)

    @Slot(bool)
    def set_pause(self, paused: bool) -> None:
        self.pause = bool(paused)

    @Slot()
    def run(self) -> None:
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
            self._timer.timeout.connect(self._poll_once)
            self._timer.setInterval(16)
        self._timer.start()

    @Slot()
    def stop(self) -> None:
        self.is_alive = False
        self.pause = True
        self.isCanceled = True
        if self._timer is not None:
            self._timer.stop()

    def _emit_legacy(self, name: str, pressed: bool) -> None:
        attr = f"{name}_{'PRESSED' if pressed else 'RELEASED'}"
        signal = getattr(self, attr, None)
        if signal is not None:
            signal.emit()
        if pressed:
            self.button_pressed.emit(name)
        else:
            self.button_released.emit(name)

    def _handle_axis_as_button(self, axis_index: int, axis_value: float) -> None:
        mapped_name = self.keymap.get(f"axis.{axis_index}")
        if mapped_name is None:
            return

        state = 1 if axis_value >= 0.5 else (-1 if axis_value <= -0.5 else 0)
        prev = self._prev_axis_button_state.get(mapped_name, 0)
        if state == prev:
            return

        if prev != 0:
            self._emit_legacy(mapped_name, False)
        if state != 0:
            self._emit_legacy(mapped_name, True)

        self._prev_axis_button_state[mapped_name] = state

    def _handle_button(self, button_index: int, pressed: bool) -> None:
        mapped_name = self.keymap.get(f"button.{button_index}")
        if mapped_name is None:
            return

        prev = self._prev_button_state.get(mapped_name, False)
        if prev == pressed:
            return

        self._prev_button_state[mapped_name] = pressed
        self._emit_legacy(mapped_name, pressed)

    def _handle_hat(self, hat_value: tuple[int, int]) -> None:
        mapping = {
            "TOP": hat_value == (0, 1),
            "BTM": hat_value == (0, -1),
            "LEFT": hat_value == (-1, 0),
            "RIGHT": hat_value == (1, 0),
        }

        for physical_name, active in mapping.items():
            mapped_name = self.keymap.get(physical_name)
            if mapped_name is None:
                continue

            prev = self._prev_hat_state.get(physical_name, False)
            if prev == active:
                continue

            self._prev_hat_state[physical_name] = active
            self._emit_legacy(mapped_name, active)

    def _emit_axis(self) -> None:
        if self.joystick_ is None:
            return

        left_h = self.joystick_.get_axis(0)
        left_v = self.joystick_.get_axis(1)
        right_h = self.joystick_.get_axis(2)
        right_v = self.joystick_.get_axis(3)

        if not self.use_Lstick:
            left_h = 0.0
            left_v = 0.0
        if not self.use_Rstick:
            right_h = 0.0
            right_v = 0.0

        self.AXIS_MOVED.emit(left_h, left_v, right_h, right_v)
        self.axis_moved.emit(left_h, left_v, right_h, right_v)

        for axis_index, axis_value in enumerate([left_h, left_v, right_h, right_v]):
            self._handle_axis_as_button(axis_index, axis_value)

    def _poll_trigger_axes(self) -> None:
        if self.joystick_ is None:
            return

        for axis_index in (4, 5):
            try:
                axis_value = self.joystick_.get_axis(axis_index)
            except Exception:
                continue
            self._handle_axis_as_button(axis_index, axis_value)

    @Slot()
    def _poll_once(self) -> None:
        if not self.is_alive:
            return

        if self.pause:
            return

        if self.no_joystick:
            # pygame.event.pump()
            # self.connect_joystick()
            return

        try:
            pygame.event.pump()

            if self.joystick_ is None:
                self.no_joystick = True
                return

            self._emit_axis()
            self._poll_trigger_axes()

            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    self._handle_button(event.button, True)
                elif event.type == pygame.JOYBUTTONUP:
                    self._handle_button(event.button, False)
                elif event.type == pygame.JOYHATMOTION:
                    self._handle_hat(event.value)
                elif event.type == pygame.JOYDEVICEREMOVED:
                    self.warning("コントローラとの接続が切断されました。")
                    self.no_joystick = True
                    self.joystick_ = None
                    self._prev_button_state.clear()
                    self._prev_axis_button_state.clear()
                    self._prev_hat_state.clear()

        except Exception as exc:
            self.error(f"Gamepad poll error: {exc}")
