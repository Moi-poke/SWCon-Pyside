from __future__ import annotations

import copy
import logging
import math
import os
import platform
import sys
from logging import getLogger
from pathlib import Path
from typing import Any, Optional
from cv2_enumerate_cameras import enumerate_cameras


import cv2
import numpy as np

import PySide6
from PySide6 import QtCore
from PySide6.QtCore import QSize, Qt, QThread, Signal, Slot
from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QColor, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget

from libs.capture import CaptureWorker
from libs.command_runtime import CommandRuntime
from libs.com_port_assist import serial_ports
from libs.CommandBase import CommandBase
from libs.CommandLoader import CommandLoader
from libs.frame_store import FrameStore
from libs.game_pad_connect import GamepadController
from libs.gui_stick_store import GuiStickStore
from libs.keys import KeyPress
from libs.mcu_command_base import McuCommand
from libs.serial_worker import SerialWorker
from libs.settings import Setting
from libs.template_match_support import TemplateMatchSupport
from libs.Utility import ospath
from ui.main_ui import Ui_MainWindow
from ui.QtextLogger import QPlainTextEditLogger

VERSION = "0.8.0 (beta)"
Author = "Moi"


class MainWindow(QMainWindow, Ui_MainWindow):
    request_capture_reopen = Signal(int)
    request_capture_set_fps = Signal(int)
    request_capture_save = Signal(object, object, object, object, str)
    request_capture_add_rect = Signal(tuple, tuple, object, int)
    request_capture_stop = Signal()
    request_capture_frame_stream = Signal(bool)

    request_serial_open = Signal(object, str)
    request_serial_close = Signal()
    request_serial_write = Signal(str, bool)
    request_serial_keypress = Signal(object, float, float, object)
    request_serial_button_pressed = Signal(str)
    request_serial_button_released = Signal(str)
    request_serial_axis = Signal(float, float, float, float)
    request_serial_show = Signal(bool)

    request_gamepad_stop = Signal()
    request_gamepad_pause = Signal(bool)
    request_gamepad_reconnect = Signal()
    request_gamepad_set_keymap = Signal(object)
    request_gamepad_set_l_stick = Signal(bool)
    request_gamepad_set_r_stick = Signal(bool)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        flags: Qt.WindowType = QtCore.Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        self.logger = getLogger(__name__)

        self.capture_thread: Optional[QThread] = None
        self.capture_worker: Optional[CaptureWorker] = None

        self.serial_thread: Optional[QThread] = None
        self.serial_worker: Optional[SerialWorker] = None

        self.gamepad_thread: Optional[QThread] = None
        self.gamepad_worker: Optional[GamepadController] = None

        self.command_runtime: Optional[CommandRuntime] = None

        self.img: Optional[QImage] = None
        self.command_mode: Optional[str] = None
        self.is_show_serial = False
        self.keymap = None
        self.mcu_cur_command = None
        self.py_cur_command = None
        self.cur_command = None
        self.template_matching_support_tool = None

        self.frame_store = FrameStore()
        self.gui_stick_store = GuiStickStore()
        self._last_preview_seq = 0
        self.preview_timer: Optional[QTimer] = None

        self.py_loader = None
        self.mcu_loader = None
        self.py_classes: list[list[Any]] = []
        self.mcu_classes: list[list[Any]] = []

        self._serial_open = False

        self.setting = Setting()

        self.setupUi(self)
        self.setWindowTitle(f"SWController {VERSION}")

        self._setup_log_widget()
        self.setFocus()

        self.set_settings()
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded")
        self.setup_functions_connect()

        self.connect_capture()
        self.connect_serial()
        self.connect_gamepad()
        self.connect_command_runtime()

        self.load_commands()
        self.show_serial()

        py_cmd = settings["command"]["py_command"]
        mcu_cmd = settings["command"]["mcu_command"]

        try:
            mcu_idx = self.comboBox_MCU.findText(mcu_cmd)
            if mcu_idx >= 0:
                self.comboBox_MCU.setCurrentIndex(mcu_idx)

            py_idx = self.comboBoxPython.findText(py_cmd)
            if py_idx >= 0:
                self.comboBoxPython.setCurrentIndex(py_idx)
        except Exception:
            self.logger.debug("There seems to have been a change in the script.")

        self._init_camera_name_list()

        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        if self.camera_list:
            target_id = str(settings["main_window"]["must"]["camera_id"])
            for i, cam in enumerate(self.camera_list):
                if str(cam["index"]) == target_id:
                    self.comboBoxCameraNames.setCurrentIndex(i)
                    break

        self.activate_serial()

        self.preview_timer = QTimer(self)
        self.preview_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.preview_timer.setInterval(16)
        self.preview_timer.timeout.connect(self.render_latest_preview)
        self.preview_timer.start()

        self._sync_command_buttons()

        if self.setting is not None:
            if self.setting.setting["main_window"]["option"]["window_showMaximized"]:
                self.showMaximized()
            else:
                self.resize(
                    self.setting.setting["main_window"]["option"]["window_size_width"],
                    self.setting.setting["main_window"]["option"]["window_size_height"],
                )

    def _setup_log_widget(self) -> None:
        self.plainTextEdit = QPlainTextEditLogger(self.dockWidgetContents)
        self.plainTextEdit.widget.setObjectName("plainTextEdit")
        self.plainTextEdit.widget.setEnabled(True)
        self.plainTextEdit.widget.setMinimumSize(QSize(500, 195))
        self.plainTextEdit.widget.setUndoRedoEnabled(True)
        self.plainTextEdit.widget.setCursorWidth(-2)
        self.plainTextEdit.widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.gridLayout.addWidget(self.plainTextEdit.widget, 0, 0, 1, 1)
        self.plainTextEdit.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.plainTextEdit)

    def _init_camera_name_list(self) -> None:
        self.camera_list: list[dict[str, object]] = []
        self.camera_dic: dict[str, str] = {}
        self.comboBoxCameraNames.clear()

        try:
            cameras = enumerate_cameras(cv2.CAP_DSHOW)
        except Exception as exc:
            self.logger.warning(
                f"Failed to enumerate cameras with cv2-enumerate-cameras: {exc}"
            )
            self.comboBoxCameraNames.setDisabled(True)
            return

        if not cameras:
            self.comboBoxCameraNames.setDisabled(True)
            self.logger.info("No cameras found on CAP_DSHOW.")
            return

        self.comboBoxCameraNames.setDisabled(False)

        for cam in cameras:
            label = f"{cam.index}: {cam.name}"
            self.comboBoxCameraNames.addItem(label)
            self.camera_list.append(
                {
                    "index": cam.index,
                    "name": cam.name,
                    "path": getattr(cam, "path", ""),
                    "backend": getattr(cam, "backend", cv2.CAP_DSHOW),
                }
            )
            self.camera_dic[str(cam.index)] = cam.name

    # ------------------------------------------------------------------
    # worker wiring
    # ------------------------------------------------------------------

    def connect_capture(self) -> None:
        self.capture_thread = QThread(self)
        try:
            camera_id = int(self.lineEditCameraID.text())
        except Exception:
            camera_id = -1

        self.capture_worker = CaptureWorker(
            camera_id=camera_id,
            frame_store=self.frame_store,
        )
        self.capture_worker.moveToThread(self.capture_thread)

        self.capture_thread.started.connect(self.capture_worker.start_capture)
        self.capture_thread.finished.connect(self.capture_worker.deleteLater)

        self.capture_worker.log.connect(
            self.callback_string_to_log,
            type=Qt.ConnectionType.QueuedConnection,
        )

        self.request_capture_reopen.connect(
            self.capture_worker.reopen_camera,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.request_capture_set_fps.connect(
            self.capture_worker.set_fps,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.request_capture_save.connect(
            self.capture_worker.save_capture,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.request_capture_add_rect.connect(
            self.capture_worker.add_rect,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.request_capture_stop.connect(
            self.capture_worker.stop_capture,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.request_capture_frame_stream.connect(
            self.capture_worker.set_frame_stream_enabled,
            type=Qt.ConnectionType.QueuedConnection,
        )

        self.capture_thread.start()

    def connect_serial(self) -> None:
        self.serial_thread = QThread(self)
        self.serial_worker = SerialWorker(
            is_show_serial=self.is_show_serial,
            keypress_factory=KeyPress,
            gui_stick_store=self.gui_stick_store,
        )

        self.serial_worker.moveToThread(self.serial_thread)

        self.serial_thread.started.connect(self.serial_worker.start)
        self.serial_thread.finished.connect(self.serial_worker.deleteLater)

        self.request_serial_open.connect(
            self.serial_worker.open_port, Qt.ConnectionType.QueuedConnection
        )
        self.request_serial_close.connect(
            self.serial_worker.close_port, Qt.ConnectionType.QueuedConnection
        )
        self.request_serial_write.connect(
            self.serial_worker.write_row, Qt.ConnectionType.QueuedConnection
        )
        self.request_serial_keypress.connect(
            self.serial_worker.on_keypress, Qt.ConnectionType.QueuedConnection
        )
        self.request_serial_button_pressed.connect(
            self.serial_worker.on_named_button_pressed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.request_serial_button_released.connect(
            self.serial_worker.on_named_button_released,
            Qt.ConnectionType.QueuedConnection,
        )
        self.request_serial_axis.connect(
            self.serial_worker.on_axis_moved, Qt.ConnectionType.QueuedConnection
        )
        self.request_serial_show.connect(
            self.serial_worker.set_show_serial, Qt.ConnectionType.QueuedConnection
        )

        self.serial_worker.log.connect(
            self.callback_string_to_log, Qt.ConnectionType.QueuedConnection
        )
        self.serial_worker.serial_error.connect(
            self.on_serial_error, Qt.ConnectionType.QueuedConnection
        )
        self.serial_worker.serial_state_changed.connect(
            self.on_serial_state_changed, Qt.ConnectionType.QueuedConnection
        )

        self.serial_thread.start()

    def connect_gamepad(self) -> None:
        self.gamepad_thread = QThread(self)
        self.gamepad_worker = GamepadController()
        self.gamepad_worker.moveToThread(self.gamepad_thread)

        self.gamepad_thread.started.connect(self.gamepad_worker.run)
        self.gamepad_thread.finished.connect(self.gamepad_worker.deleteLater)

        self.request_gamepad_stop.connect(
            self.gamepad_worker.stop, Qt.ConnectionType.QueuedConnection
        )
        self.request_gamepad_pause.connect(
            self.gamepad_worker.set_pause, Qt.ConnectionType.QueuedConnection
        )
        self.request_gamepad_reconnect.connect(
            self.gamepad_worker.connect_joystick, Qt.ConnectionType.QueuedConnection
        )

        self.request_gamepad_set_keymap.connect(
            self.gamepad_worker.set_keymap,
            Qt.ConnectionType.QueuedConnection,
        )
        self.request_gamepad_set_l_stick.connect(
            self.gamepad_worker.set_l_stick,
            Qt.ConnectionType.QueuedConnection,
        )
        self.request_gamepad_set_r_stick.connect(
            self.gamepad_worker.set_r_stick,
            Qt.ConnectionType.QueuedConnection,
        )

        self.gamepad_worker.button_pressed.connect(
            self.handle_gamepad_button_pressed, Qt.ConnectionType.QueuedConnection
        )
        self.gamepad_worker.button_released.connect(
            self.handle_gamepad_button_released, Qt.ConnectionType.QueuedConnection
        )
        self.gamepad_worker.axis_moved.connect(
            self.handle_gamepad_axis_moved, Qt.ConnectionType.QueuedConnection
        )
        self.gamepad_worker.log.connect(
            self.callback_string_to_log, Qt.ConnectionType.QueuedConnection
        )

        self.gamepad_thread.start()
        self.request_gamepad_set_keymap.emit(self.keymap)
        self.gamepad_l_stick()
        self.gamepad_r_stick()

    def connect_command_runtime(self) -> None:
        self.command_runtime = CommandRuntime(self.frame_store, self)
        self.command_runtime.log.connect(
            self.callback_string_to_log,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.command_runtime.started.connect(
            self.on_command_started,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.command_runtime.stopped.connect(
            self.on_command_stopped,
            type=Qt.ConnectionType.QueuedConnection,
        )

    @Slot()
    def render_latest_preview(self) -> None:
        image, seq = self.frame_store.get_preview_if_new(self._last_preview_seq)
        if image is None:
            return

        self._last_preview_seq = seq
        self.img = image
        pix = QPixmap.fromImage(image)
        self.CaptureImageArea.setPixmap(pix)

    # ------------------------------------------------------------------
    # UI wiring
    # ------------------------------------------------------------------
    def setup_functions_connect(self) -> None:
        self.pushButtonReloadCamera.pressed.connect(
            lambda: self.reconnect_camera(self.lineEditCameraID.text())
        )
        self.pushButtonReloadCamera.pressed.connect(self.reload_camera)

        self.pushButtonClearLog.pressed.connect(self.plainTextEdit.widget.clear)

        self.pushButton_PythonStart.pressed.connect(self.start_command)
        self.pushButton_PythonStop.pressed.connect(
            lambda: self.stop_command(block=False)
        )
        self.pushButton_MCUStart.pressed.connect(self.start_mcu_command)
        self.pushButton_MCUStop.pressed.connect(self.stop_mcu_command)

        self.pushButton_PythonReload.clicked.connect(self.reload_commands)
        self.pushButton_MCUReload.clicked.connect(self.reload_commands)
        self.pushButtonReloadPort.clicked.connect(self.activate_serial)

        self.pushButtonScreenShot.clicked.connect(self.screen_shot)
        self.toolButtonOpenScreenShotDir.clicked.connect(self.open_screen_shot_dir)
        self.toolButtonOpenPythonDir.clicked.connect(self.open_python_shot_dir)
        self.toolButton_OpenMCUDir.clicked.connect(self.open_mcu_shot_dir)
        self.comboBoxCameraNames.currentIndexChanged.connect(
            self.handle_camera_selection_changed
        )
        self.tabWidget.currentChanged.connect(self.set_command_mode)
        self.tabWidget.currentChanged.connect(self.assign_command)
        self.comboBoxPython.currentIndexChanged.connect(self.assign_command)
        self.comboBox_MCU.currentIndexChanged.connect(self.assign_command)

        self.left_stick.stick_signal.connect(self.handle_gui_stick_left)
        self.right_stick.stick_signal.connect(self.handle_gui_stick_right)

        self.CaptureImageArea.mousePressEvent = self.capture_mouse_press_event

        self.lineEditFPS.textChanged.connect(self.assign_fps_to_setting)
        self.lineEditCameraID.textChanged.connect(self.assign_camera_id_to_setting)
        self.lineEditComPort.textChanged.connect(self.assign_com_port_to_setting)
        self.comboBox_MCU.currentIndexChanged.connect(
            self.assign_mcu_command_to_setting
        )
        self.comboBoxPython.currentIndexChanged.connect(
            self.assign_py_command_to_setting
        )

        self.actionconnect.triggered.connect(self.reconnect_gamepad)
        self.actionCOM_Port_ASSIST.triggered.connect(
            self.message_show_available_com_port
        )
        self.actionShow_Serial.triggered.connect(self.show_serial)
        self.actionPauseController.triggered.connect(self.pause_controller)

        self._connect_controller_buttons()

    def _connect_controller_buttons(self) -> None:
        mapping = {
            "BTN_zl": "ZL",
            "BTN_l": "L",
            "BTN_ls": "LCLICK",
            "BTN_minus": "MINUS",
            "BTN_up": "TOP",
            "BTN_down": "BTM",
            "BTN_left": "LEFT",
            "BTN_right": "RIGHT",
            "BTN_capture": "CAPTURE",
            "BTN_zr": "ZR",
            "BTN_r": "R",
            "BTN_rs": "RCLICK",
            "BTN_plus": "PLUS",
            "BTN_a": "A",
            "BTN_b": "B",
            "BTN_x": "X",
            "BTN_y": "Y",
            "BTN_home": "HOME",
        }
        for widget_name, logical_name in mapping.items():
            widget = getattr(self, widget_name, None)
            if widget is None:
                continue
            widget.pressed.connect(
                lambda name=logical_name: self.on_ui_button_pressed(name)
            )
            widget.released.connect(
                lambda name=logical_name: self.on_ui_button_released(name)
            )

    # ------------------------------------------------------------------
    # settings
    # ------------------------------------------------------------------
    def assign_fps_to_setting(self) -> None:
        self.setting.setting["main_window"]["must"]["fps"] = self.lineEditFPS.text()

    def assign_camera_id_to_setting(self) -> None:
        self.setting.setting["main_window"]["must"]["camera_id"] = (
            self.lineEditCameraID.text()
        )

    def assign_com_port_to_setting(self) -> None:
        self.setting.setting["main_window"]["must"]["com_port"] = (
            self.lineEditComPort.text()
        )

    def assign_window_size_to_setting(self) -> None:
        self.setting.setting["main_window"]["option"]["window_size_width"] = (
            self.width()
        )
        self.setting.setting["main_window"]["option"]["window_size_height"] = (
            self.height()
        )

    def assign_mcu_command_to_setting(self) -> None:
        self.setting.setting["command"]["mcu_command"] = self.comboBox_MCU.itemText(
            self.comboBox_MCU.currentIndex()
        )

    def assign_py_command_to_setting(self) -> None:
        self.setting.setting["command"]["py_command"] = self.comboBoxPython.itemText(
            self.comboBoxPython.currentIndex()
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.assign_window_size_to_setting()
        super().resizeEvent(event)

    def set_settings(self) -> None:
        try:
            self.logger.debug("Load setting")
            self.setting.load()
        except FileNotFoundError:
            self.logger.debug("File Not FoundGenerate setting")
            self.setting.generate()
            self.setting.load()

        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        self.lineEditFPS.setText(str(settings["main_window"]["must"]["fps"]))
        self.lineEditCameraID.setText(str(settings["main_window"]["must"]["camera_id"]))
        self.lineEditComPort.setText(str(settings["main_window"]["must"]["com_port"]))
        self.actionShow_Serial.setChecked(
            settings["main_window"]["option"]["show_serial"]
        )

        self.keymap = {
            v["assign"]: k
            for k, v in settings["key_config"]["joystick"]["button"].items()
            if v["state"]
        } | {
            v["assign"]: k
            for k, v in settings["key_config"]["joystick"]["hat"].items()
            if v["state"]
        }

    # ------------------------------------------------------------------
    # serial / capture / gamepad controls
    # ------------------------------------------------------------------
    def activate_serial(self) -> None:
        self.request_serial_close.emit()
        self.request_serial_open.emit(
            self.setting.setting["main_window"]["must"]["com_port"], ""
        )

    def on_serial_state_changed(self, opened: bool, label: str) -> None:
        self._serial_open = opened
        if opened:
            self.logger.info(f"Serial connected: {label}")
        else:
            self.logger.info("Serial disconnected")

    def on_serial_error(self, message: str) -> None:
        self.logger.error(message)

    def reconnect_camera(self, cam_id: str) -> None:
        try:
            self.request_capture_reopen.emit(int(cam_id))
        except ValueError:
            self.logger.error(f"Invalid camera id: {cam_id}")

    def reload_camera(self) -> None:
        try:
            self.request_capture_set_fps.emit(
                int(self.setting.setting["main_window"]["must"]["fps"])
            )
        except Exception as exc:
            self.logger.error(exc)

    def reconnect_gamepad(self) -> None:
        self.request_gamepad_reconnect.emit()

    def pause_controller(self) -> None:
        paused = self.actionPauseController.isChecked()
        if paused:
            self.logger.info("コントローラ入力を一時停止します")
        else:
            self.logger.info("コントローラ入力を再開します")
        self.request_gamepad_pause.emit(paused)

    def show_serial(self) -> None:
        enabled = self.actionShow_Serial.isChecked()
        self.setting.setting["main_window"]["option"]["show_serial"] = enabled
        self.is_show_serial = enabled
        self.request_serial_show.emit(enabled)

    # ------------------------------------------------------------------
    # commands
    # ------------------------------------------------------------------
    def load_commands(self) -> None:
        self.py_loader = CommandLoader(ospath("Commands/Python"), CommandBase)
        self.mcu_loader = CommandLoader(ospath("Commands/MCU"), McuCommand)

        self.py_classes, py_error = self.py_loader.load()
        self.mcu_classes, mcu_error = self.mcu_loader.load()

        self._log_loader_errors(py_error)
        self._log_loader_errors(mcu_error)

        self.set_command_items()
        self.assign_command()

    def _log_loader_errors(self, error_dict: dict) -> None:
        if not error_dict:
            return
        for k, v in error_dict.items():
            if len(v) >= 3:
                self.logger.error(f"Error while loading {k}\n>>> {v[1]}\n{v[2]}")
            else:
                self.logger.error(f"Error while loading {k}\n>>> {v}")

    def set_command_items(self) -> None:
        self.comboBoxPython.clear()
        self.comboBox_MCU.clear()

        for idx, item in enumerate(self.py_classes):
            cls = item[0]
            self.comboBoxPython.addItem(cls.NAME)
            tip = getattr(cls(), "__tool_tip__", None)
            if tip is not None:
                self.comboBoxPython.setItemData(idx, tip, QtCore.Qt.ToolTipRole)
            self.comboBoxPython.setItemData(
                idx, QColor(255, 0, 0), QtCore.Qt.ItemDataRole.ForegroundRole
            )

        for item in self.mcu_classes:
            cls = item[0]
            self.comboBox_MCU.addItem(cls.NAME)

        if self.comboBoxPython.count() > 0:
            self.comboBoxPython.setCurrentIndex(0)
        if self.comboBox_MCU.count() > 0:
            self.comboBox_MCU.setCurrentIndex(0)

    def assign_command(self) -> None:
        if self.mcu_classes and 0 <= self.comboBox_MCU.currentIndex() < len(
            self.mcu_classes
        ):
            self.mcu_cur_command = self.mcu_classes[self.comboBox_MCU.currentIndex()][0]
        else:
            self.mcu_cur_command = None

        if self.py_classes and 0 <= self.comboBoxPython.currentIndex() < len(
            self.py_classes
        ):
            self.py_cur_command = self.py_classes[self.comboBoxPython.currentIndex()][0]
        else:
            self.py_cur_command = None

        if self.tabWidget.currentIndex() == 0:
            self.cur_command = self.py_cur_command
        else:
            self.cur_command = self.mcu_cur_command

    def _sync_command_buttons(self) -> None:
        python_running = (
            self.command_runtime is not None and self.command_runtime.is_running()
        )
        mcu_running = getattr(self, "_mcu_command", None) is not None

        self.pushButton_PythonStart.setEnabled(not python_running)
        self.pushButton_PythonStop.setEnabled(python_running)

        self.pushButton_MCUStart.setEnabled(not mcu_running)
        self.pushButton_MCUStop.setEnabled(mcu_running)

    def set_command_mode(self) -> None:
        if self.tabWidget.currentIndex() == 0:
            self.command_mode = "python"
        elif self.tabWidget.currentIndex() == 1:
            self.command_mode = "mcu"
        else:
            raise Exception("Unknown command mode")

    def start_command(self) -> None:

        if (
            self.command_runtime is None
            or self.serial_worker is None
            or self.capture_worker is None
        ):
            self.logger.error("Command runtime is not ready.")
            return
        if self.cur_command is None:
            self.logger.error("No command is selected.")
            return

        self.stop_command(block=True)
        self.request_gamepad_pause.emit(True)
        self.request_capture_frame_stream.emit(True)

        started = self.command_runtime.start(
            self.cur_command, self.serial_worker, self.capture_worker
        )
        if not started:
            self.request_gamepad_pause.emit(False)
            self.request_capture_frame_stream.emit(False)

        self._sync_command_buttons()

    def on_command_started(self, name: str) -> None:
        self.logger.info(f"Command started: {name}")

    def stop_command(self, block: bool = False) -> None:
        if self.command_runtime is None or not self.command_runtime.is_running():
            self.request_capture_frame_stream.emit(False)
            self._sync_command_buttons()
            return

        self.logger.debug("Send stop request to command runtime.")
        self.command_runtime.stop(block=block)
        self.request_capture_frame_stream.emit(False)
        self._sync_command_buttons()

    def on_command_stopped(self, result: bool) -> None:

        _ = result
        self.request_gamepad_pause.emit(False)
        self.request_capture_frame_stream.emit(False)
        self._sync_command_buttons()

    def start_mcu_command(self) -> None:

        self.assign_command()
        if self.cur_command is None:
            self.logger.error("No MCU command is selected.")
            return

        self._mcu_command = self.cur_command()
        self._mcu_command.play_sync_name.connect(
            self.play_mcu, Qt.ConnectionType.QueuedConnection
        )
        self._mcu_command.start()

        self._sync_command_buttons()

    def stop_mcu_command(self) -> None:

        if getattr(self, "_mcu_command", None) is None:
            self._sync_command_buttons()
            return

        self._mcu_command.end()
        self._mcu_command.play_sync_name.disconnect()
        self._mcu_command = None

        self._sync_command_buttons()

    @Slot(str)
    def play_mcu(self, s: str) -> None:
        self.request_serial_write.emit(s, False)

    def reload_commands(self) -> None:
        self.stop_command(block=True)

        old_val_mcu = self.comboBox_MCU.itemText(self.comboBox_MCU.currentIndex())
        old_val_py = self.comboBoxPython.itemText(self.comboBoxPython.currentIndex())

        self.py_classes, py_reload_error = self.py_loader.reload()
        self.mcu_classes, mcu_reload_error = self.mcu_loader.reload()

        self.set_command_items()

        mcu_idx = self.comboBox_MCU.findText(old_val_mcu)
        if mcu_idx != -1:
            self.comboBox_MCU.setCurrentIndex(mcu_idx)
        elif self.comboBox_MCU.count() > 0:
            self.comboBox_MCU.setCurrentIndex(0)

        py_idx = self.comboBoxPython.findText(old_val_py)
        if py_idx != -1:
            self.comboBoxPython.setCurrentIndex(py_idx)
        elif self.comboBoxPython.count() > 0:
            self.comboBoxPython.setCurrentIndex(0)

        self.assign_command()

        if not py_reload_error and not mcu_reload_error:
            self.logger.info("Reloaded commands.")
        else:
            self._log_loader_errors(py_reload_error)
            self._log_loader_errors(mcu_reload_error)

    # ------------------------------------------------------------------
    # UI/gamepad/button handling
    # ------------------------------------------------------------------
    def on_ui_button_pressed(self, name: str) -> None:
        self._set_button_checked(name, True)
        self.request_serial_button_pressed.emit(name)

    def on_ui_button_released(self, name: str) -> None:
        self._set_button_checked(name, False)
        self.request_serial_button_released.emit(name)

    @Slot(int)
    def handle_camera_selection_changed(self, index: int) -> None:
        if not hasattr(self, "camera_list"):
            return
        if index < 0 or index >= len(self.camera_list):
            return

        selected = self.camera_list[index]
        cam_index = int(selected["index"])

        self.lineEditCameraID.setText(str(cam_index))
        self.request_capture_reopen.emit(cam_index)

        self.logger.info(f"Selected camera: {selected['name']} (index={cam_index})")

    @Slot(str)
    def handle_gamepad_button_pressed(self, name: str) -> None:
        self._set_button_checked(name, True)
        self.request_serial_button_pressed.emit(name)

    @Slot(str)
    def handle_gamepad_button_released(self, name: str) -> None:
        self._set_button_checked(name, False)
        self.request_serial_button_released.emit(name)

    @Slot(float, float, float, float)
    def handle_gamepad_axis_moved(
        self,
        left_horizontal: float,
        left_vertical: float,
        right_horizontal: float,
        right_vertical: float,
    ) -> None:
        self.stickMoveEvent(
            left_horizontal, left_vertical, right_horizontal, right_vertical
        )
        self.request_serial_axis.emit(
            left_horizontal, left_vertical, right_horizontal, right_vertical
        )

    def _set_button_checked(self, name: str, checked: bool) -> None:
        mapping = {
            "ZL": "BTN_zl",
            "L": "BTN_l",
            "LCLICK": "BTN_ls",
            "MINUS": "BTN_minus",
            "TOP": "BTN_up",
            "BTM": "BTN_down",
            "LEFT": "BTN_left",
            "RIGHT": "BTN_right",
            "CAPTURE": "BTN_capture",
            "ZR": "BTN_zr",
            "R": "BTN_r",
            "RCLICK": "BTN_rs",
            "PLUS": "BTN_plus",
            "A": "BTN_a",
            "B": "BTN_b",
            "X": "BTN_x",
            "Y": "BTN_y",
            "HOME": "BTN_home",
        }
        widget_name = mapping.get(name)
        if widget_name is None:
            return
        widget = getattr(self, widget_name, None)
        if widget is not None:
            widget.setChecked(checked)

    @Slot(float, float)
    def handle_gui_stick_left(self, angle: float, r: float) -> None:
        self.gui_stick_store.set_left(float(angle), float(r))

    @Slot(float, float)
    def handle_gui_stick_right(self, angle: float, r: float) -> None:
        self.gui_stick_store.set_right(float(angle), float(r))

    def stickMoveEvent(
        self, left_horizontal, left_vertical, right_horizontal, right_vertical
    ) -> None:
        try:
            left_angle = math.atan2(left_vertical, left_horizontal)
            left_r = math.sqrt(left_vertical**2 + left_horizontal**2)
            right_angle = math.atan2(right_vertical, right_horizontal)
            right_r = math.sqrt(right_vertical**2 + right_horizontal**2)

            dead_zone = 0.35
            if left_r < dead_zone:
                left_r = 0
            else:
                left_r = (left_r - dead_zone) / (1 - dead_zone)

            if right_r < dead_zone:
                right_r = 0
            else:
                right_r = (right_r - dead_zone) / (1 - dead_zone)

            self.left_stick.stickMoveEvent(left_r, left_angle)
            self.right_stick.stickMoveEvent(right_r, right_angle)
        except KeyboardInterrupt:
            self.close()

    def gamepad_l_stick(self) -> None:

        enabled = bool(
            self.setting.setting["key_config"]["joystick"]["direction"]["LStick"]
        )
        self.request_gamepad_set_l_stick.emit(enabled)

    def gamepad_r_stick(self) -> None:

        enabled = bool(
            self.setting.setting["key_config"]["joystick"]["direction"]["RStick"]
        )
        self.request_gamepad_set_r_stick.emit(enabled)

    # ------------------------------------------------------------------
    # image / logging / utility
    # ------------------------------------------------------------------

    @Slot(str, int)
    def callback_string_to_log(self, s, level) -> None:
        match level:
            case logging.DEBUG:
                self.logger.debug(s)
            case logging.INFO:
                self.logger.info(s)
            case logging.WARNING:
                self.logger.warning(s)
            case logging.ERROR:
                self.logger.error(s)
            case logging.CRITICAL:
                self.logger.critical(s)
            case logging.FATAL:
                self.logger.fatal(s)
            case _:
                self.logger.info(s)

    def screen_shot(self) -> None:
        try:
            capture_dir = (
                self.cur_command.CAPTURE_DIR
                if self.cur_command is not None
                else "./ScreenShot"
            )
            self.request_capture_save.emit(None, None, None, None, capture_dir)
        except Exception as exc:
            self.logger.error(exc)

    def capture_mouse_press_event(self, event) -> None:
        if self.img is None:
            return
        if event.modifiers() & QtCore.Qt.ControlModifier:
            w = self.CaptureImageArea.width()
            h = self.CaptureImageArea.height()
            x = event.position().x()
            x_ = int(x * 1280 / w)
            y = event.position().y()
            y_ = int(y * 720 / h)
            c = self.img.pixel(x_, y_)
            c_rgb = QColor(c).getRgb()
            self.logger.debug(
                f"Clicked at x:{x_} y:{y_}, R:{c_rgb[0]} G:{c_rgb[1]} B: {c_rgb[2]}"
            )
            return x, y, c_rgb

    def open_screen_shot_dir(self) -> None:
        target = os.path.realpath(
            self.cur_command.CAPTURE_DIR
            if self.cur_command is not None
            else "./ScreenShot"
        )
        self._open_path(target)

    def open_python_shot_dir(self) -> None:
        if self.cur_command is None:
            return
        self._open_path(
            os.path.realpath(Path(self.cur_command.__directory__).resolve().parent)
        )

    def open_mcu_shot_dir(self) -> None:
        if self.cur_command is None:
            return
        self._open_path(os.path.realpath(self.cur_command.__directory__))

    def _open_path(self, target: str) -> None:
        try:
            if hasattr(os, "startfile"):
                os.startfile(target)
            else:
                self.logger.info(f"Open path manually: {target}")
        except Exception as exc:
            self.logger.error(exc)

    @staticmethod
    def message_show_available_com_port() -> None:
        ls = serial_ports()
        QMessageBox.information(
            None,
            "利用可能なCOMポート",
            f"利用可能なCOMポートは\n{','.join(ls)}\nです。",
            QMessageBox.Ok,
        )

    def open_template_matching_support_tool(self) -> None:
        self.logger.debug("テンプレートマッチ補助ツール")
        if self.template_matching_support_tool is None:
            self.template_matching_support_tool = TemplateMatchSupport()
            self.template_matching_support_tool.get_image.connect(
                self.callback_set_template_matching_support_tool
            )
            self.template_matching_support_tool.graphicsView.template_matching.connect(
                self.callback_template_matching
            )
            self.template_matching_support_tool.print_strings.connect(
                self.callback_string_to_log, Qt.ConnectionType.QueuedConnection
            )
        self.template_matching_support_tool.show()

    @Slot()
    def callback_set_template_matching_support_tool(self) -> None:
        if self.template_matching_support_tool is None:
            return

        frame = self.frame_store.latest_raw_copy()
        if frame is None:
            self.logger.warning("No latest raw frame available for template tool.")
            return

        self.template_matching_support_tool.image = copy.deepcopy(frame)
        self.logger.debug("Set Image to tool.")

    @Slot()
    def callback_template_matching(self) -> None:
        if self.template_matching_support_tool is not None:
            self.template_matching_support_tool.create_scene(get_img=False)

    # ------------------------------------------------------------------
    # shutdown
    # ------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:

        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        if self.preview_timer is not None:
            self.preview_timer.stop()
        if self.isMaximized():
            settings["main_window"]["option"]["window_showMaximized"] = True
        else:
            settings["main_window"]["option"]["window_showMaximized"] = False

        settings["command"]["py_command"] = self.comboBoxPython.currentText()
        settings["command"]["mcu_command"] = self.comboBox_MCU.currentText()

        if self.template_matching_support_tool is not None:
            self.template_matching_support_tool.close()

        # 1. UIから新規操作を止める
        self.setEnabled(False)

        # 2. command stop
        self.stop_command(block=True)
        self.request_capture_frame_stream.emit(False)

        # 3. gamepad stop
        self.request_gamepad_pause.emit(True)
        self.request_gamepad_stop.emit()

        # 4. capture stop
        self.request_capture_stop.emit()

        # 5. line worker は omit のためなし

        # 6. serial close
        self.request_serial_close.emit()

        # 7. thread quit/wait
        if self.gamepad_thread is not None:
            self.gamepad_thread.quit()
            self.gamepad_thread.wait(3000)

        if self.capture_thread is not None:
            self.capture_thread.quit()
            self.capture_thread.wait(3000)

        if self.serial_thread is not None:
            self.serial_thread.quit()
            self.serial_thread.wait(3000)

        # 8. 設定保存
        self.setting.save()
        self.logger.debug("Save settings")

        super().closeEvent(event)


if __name__ == "__main__":
    logger = logging.Logger(__name__)

    dirname = os.path.dirname(PySide6.__file__)
    pluginPath = os.path.join(dirname, "plugins", "platforms")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = pluginPath

    try:
        with open("ui/style.qss", "r", encoding="utf-8") as f:
            style = f.read()
    except Exception:
        style = ""

    try:
        app = QApplication(sys.argv)
        app.setStyleSheet(style)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.exception(e)
        print("quit")
