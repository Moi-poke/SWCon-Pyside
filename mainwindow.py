from __future__ import annotations

import copy
import json
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
from PySide6.QtGui import QCloseEvent, QColor, QImage, QPixmap, QResizeEvent, QAction
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QWidget,
)

from libs.capture import CaptureWorker
from libs.command_catalog import CommandCatalog, CommandDescriptor
from libs.command_models import CommandExecutionContext, CommandTriggerSource
from libs.command_runtime import CommandRuntime
from libs.command_session_controller import CommandSessionController
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
from libs.visual_macro.editor_widget import VisualMacroEditorWidget
from libs.visual_macro.factory import build_visual_macro_command_class
from libs.visual_macro.repository import VisualMacroRepository
from ui.main_ui import Ui_MainWindow
from ui.QtextLogger import QPlainTextEditLogger

VERSION = "0.9.1 (beta)"
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
        self.command_session: Optional[CommandSessionController] = None
        self.command_catalog: Optional[CommandCatalog] = None

        self.current_python_descriptor: Optional[CommandDescriptor] = None
        self.current_mcu_descriptor: Optional[CommandDescriptor] = None
        self.current_visual_descriptor: Optional[CommandDescriptor] = None
        self.current_descriptor: Optional[CommandDescriptor] = None

        self.visual_macro_repository = VisualMacroRepository()
        self.visual_macro_dock: Optional[QDockWidget] = None
        self.visual_macro_editor: Optional[VisualMacroEditorWidget] = None
        self._visual_macro_command_class: Optional[type[CommandBase]] = None
        self.visual_macro_toggle_action: Optional[QAction] = None
        self._visual_macro_current_relative_path: str = ""
        self._visual_macro_current_path: str = ""
        self._visual_macro_is_modified: bool = False
        self._visual_macro_restore_scheduled: bool = False
        self._visual_macro_run_request_in_flight: bool = False
        self._syncing_visual_macro_selection: bool = False

        self.img: Optional[QImage] = None
        self.command_mode: Optional[str] = None
        self.is_show_serial = False
        self.keymap = None
        self.mcu_cur_command: Optional[type[McuCommand]] = None
        self.py_cur_command: Optional[type[CommandBase]] = None
        self.cur_command: Optional[type] = None
        self.template_matching_support_tool = None

        self.frame_store = FrameStore()
        self.gui_stick_store = GuiStickStore()
        self._last_preview_seq = 0
        self.preview_timer: Optional[QTimer] = None

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
        self.setup_visual_macro_editor()

        self.load_commands()
        self.show_serial()

        py_cmd = settings["command"]["py_command"]
        mcu_cmd = settings["command"]["mcu_command"]
        visual_cmd = settings["command"].get("visual_macro_command", "")

        try:
            mcu_idx = self.comboBox_MCU.findText(mcu_cmd)
            if mcu_idx >= 0:
                self.comboBox_MCU.setCurrentIndex(mcu_idx)

            py_idx = self.comboBoxPython.findText(py_cmd)
            if py_idx >= 0:
                self.comboBoxPython.setCurrentIndex(py_idx)

            if visual_cmd:
                visual_idx = self.comboBox_VisualMacro.findText(visual_cmd)
                if visual_idx >= 0:
                    self.comboBox_VisualMacro.setCurrentIndex(visual_idx)

        except Exception:
            self.logger.debug("There seems to have been a change in the script.")

        self._init_camera_name_list()

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

        if settings["main_window"]["option"]["window_showMaximized"]:
            self.showMaximized()
        else:
            self.resize(
                settings["main_window"]["option"]["window_size_width"],
                settings["main_window"]["option"]["window_size_height"],
            )

    # ------------------------------------------------------------------
    # logging
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # camera list
    # ------------------------------------------------------------------
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
        self.command_runtime.highlight_block_requested.connect(
            self.on_visual_macro_highlight_requested,
            type=Qt.ConnectionType.QueuedConnection,
        )
        self.command_runtime.clear_block_highlight_requested.connect(
            self.on_visual_macro_highlight_cleared,
            type=Qt.ConnectionType.QueuedConnection,
        )

        self.command_session = CommandSessionController(
            logger=self.logger,
            command_runtime=self.command_runtime,
            serial_worker=self.serial_worker,
            capture_worker=self.capture_worker,
            pause_gamepad=lambda paused: self.request_gamepad_pause.emit(paused),
            set_frame_stream=lambda enabled: self.request_capture_frame_stream.emit(
                enabled
            ),
            sync_buttons=self._sync_command_buttons,
            play_mcu_callback=self.play_mcu,
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
    # visual macro
    # ------------------------------------------------------------------

    @Slot(str)
    def on_visual_macro_highlight_requested(self, block_id: str) -> None:
        if self.visual_macro_editor is None:
            return
        self.visual_macro_editor.bridge.highlight_block_requested.emit(block_id)

    @Slot()
    def on_visual_macro_highlight_cleared(self) -> None:
        if self.visual_macro_editor is None:
            return
        self.visual_macro_editor.bridge.clear_block_highlight_requested.emit()

    def _normalize_visual_macro_relative_path(self, source_path: str) -> str:
        """Normalize a stored or absolute path into Commands/Visual-relative form."""
        try:
            return self.visual_macro_repository.to_relative_path(source_path)
        except Exception:
            return source_path.replace("\\", "/").lstrip("./")

    def _find_visual_macro_combo_index_by_source_path(self, source_path: str) -> int:
        """Return the VM combo index for a given source path, or -1 if not found."""
        if self.command_catalog is None:
            return -1

        target = self._normalize_visual_macro_relative_path(source_path)

        for index, descriptor in enumerate(self.command_catalog.visual_descriptors):
            descriptor_path = self._normalize_visual_macro_relative_path(
                descriptor.source_path
            )
            if descriptor_path == target:
                return index

        return -1

    def _set_visual_macro_combo_index_safely(self, index: int) -> None:
        """Set the VM combo index without triggering recursive sync side effects."""
        self._syncing_visual_macro_selection = True
        try:
            self.comboBox_VisualMacro.blockSignals(True)
            self.comboBox_VisualMacro.setCurrentIndex(index)
        finally:
            self.comboBox_VisualMacro.blockSignals(False)
            self._syncing_visual_macro_selection = False

        self.assign_command()
        self.assign_visual_macro_command_to_setting()

    def _sync_visual_macro_combo_from_editor(self, relative_path: str) -> None:
        """Sync the VM combo selection from the editor's current document path."""
        normalized = self._normalize_visual_macro_relative_path(relative_path)

        if not normalized:
            # editor が無題状態なら VM 一覧選択は外す
            self._set_visual_macro_combo_index_safely(-1)
            self.current_visual_descriptor = None
            return

        index = self._find_visual_macro_combo_index_by_source_path(normalized)
        if index >= 0:
            self._set_visual_macro_combo_index_safely(index)
            return

        # Save As などで新規ファイルができた可能性があるので一覧を再読込して再検索
        self.reload_commands()

        index = self._find_visual_macro_combo_index_by_source_path(normalized)
        if index >= 0:
            self._set_visual_macro_combo_index_safely(index)

    def open_visual_macro_dir(self) -> None:
        target = os.path.realpath(ospath("Commands/Visual"))
        self._open_path(target)

    def open_selected_visual_macro_in_editor(self) -> None:
        self.assign_command()

        descriptor = self.current_visual_descriptor
        if descriptor is None:
            self.logger.error("No Visual Macro is selected.")
            return

        if self.visual_macro_editor is None:
            self.logger.error("Visual Macro editor is not available.")
            return

        relative_path = self.visual_macro_repository.to_relative_path(
            descriptor.source_path
        )
        self.show_visual_macro_editor()
        self.visual_macro_editor.open_document_by_path(relative_path)

    def start_visual_catalog_command(self) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return

        self.assign_command()

        descriptor = self.current_visual_descriptor
        if descriptor is None:
            self.logger.error("No Visual Macro is selected.")
            return

        try:
            document = self.visual_macro_repository.load_document(
                descriptor.source_path
            )
            metadata = document.get("metadata", {})
            program = document["program"]

            metadata_name = str(metadata.get("name", "")).strip()
            display_name = metadata_name or descriptor.display_name or "Visual Macro"

            program_json = json.dumps(program, ensure_ascii=False)

            visual_macro_class = build_visual_macro_command_class(
                program_json=program_json,
                display_name=display_name,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to load/run saved Visual Macro: {exc}")
            QMessageBox.warning(
                self,
                "Visual Macro",
                f"保存済み Visual Macro の実行準備に失敗しました。\n{exc}",
            )
            return

        context = CommandExecutionContext(
            command_id=descriptor.command_id,
            kind=descriptor.kind.value,
            display_name=display_name,
            source_path=descriptor.source_path,
            trigger_source=CommandTriggerSource.UI_COMBO.value,
            payload_json=program_json,
        )

        self.current_visual_descriptor = descriptor
        self._visual_macro_command_class = visual_macro_class
        self.current_python_descriptor = None
        self.current_descriptor = descriptor
        self.py_cur_command = visual_macro_class
        self.cur_command = visual_macro_class
        self.command_mode = "python"

        started = self.command_session.start_visual_command(
            visual_macro_class,
            context,
        )
        if not started:
            self.logger.error("Saved Visual Macro start request was rejected.")

    def setup_visual_macro_editor(self) -> None:
        """Create and attach the Visual Macro editor dock."""
        dock = QDockWidget("Visual Macro", self)
        editor = VisualMacroEditorWidget(parent=dock)

        dock.setObjectName("dockWidgetVisualMacro")
        dock.setWidget(editor)

        dock.setFeatures(
            QDockWidget.DockWidgetFeatures.DockWidgetClosable
            # | QDockWidget.DockWidgetFeatures.DockWidgetMovable
            | QDockWidget.DockWidgetFeatures.DockWidgetFloatable
        )
        dock.setAllowedAreas(
            Qt.DockWidgetArea.NoDockWidgetArea
            # Qt.DockWidgetArea.LeftDockWidgetArea
            # | Qt.DockWidgetArea.RightDockWidgetArea
            # | Qt.DockWidgetArea.BottomDockWidgetArea
            # | Qt.DockWidgetArea.TopDockWidgetArea
        )

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        dock.setFloating(True)

        self.visual_macro_dock = dock
        self.visual_macro_editor = editor

        editor.run_requested.connect(
            self.on_visual_macro_run_requested,
            Qt.ConnectionType.QueuedConnection,
        )
        editor.stop_requested.connect(
            self.on_visual_macro_stop_requested,
            Qt.ConnectionType.QueuedConnection,
        )
        editor.status_message.connect(
            self.on_visual_macro_status_message,
            Qt.ConnectionType.QueuedConnection,
        )

        # すでに入れているならそのまま使ってOK
        if hasattr(self, "_setup_visual_macro_toggle_action"):
            self._setup_visual_macro_toggle_action()

        editor.document_state_changed.connect(
            self.on_visual_macro_document_state_changed,
            Qt.ConnectionType.QueuedConnection,
        )

        self._update_visual_macro_dock_title()
        self._schedule_restore_visual_macro_dock_state()

    def _schedule_restore_visual_macro_dock_state(self) -> None:
        """Restore the Visual Macro dock state after the event loop starts."""
        if self._visual_macro_restore_scheduled:
            return
        self._visual_macro_restore_scheduled = True
        QTimer.singleShot(0, self._restore_visual_macro_dock_state)

    def _visual_macro_dock_settings(self) -> dict[str, object]:
        """Return the persisted settings dictionary for the Visual Macro dock."""
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        main_window = settings.setdefault("main_window", {})
        option = main_window.setdefault("option", {})
        dock_state = option.setdefault("visual_macro_dock", {})
        return dock_state

    def _dock_area_to_int(self, area: Qt.DockWidgetArea) -> int:
        """Convert a DockWidgetArea enum into an int for JSON-like settings."""
        return int(area.value) if hasattr(area, "value") else int(area)

    def _int_to_dock_area(self, value: object) -> Qt.DockWidgetArea:
        """Convert a stored integer back to a DockWidgetArea."""
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return Qt.DockWidgetArea.RightDockWidgetArea

        candidates = (
            Qt.DockWidgetArea.LeftDockWidgetArea,
            Qt.DockWidgetArea.RightDockWidgetArea,
            Qt.DockWidgetArea.TopDockWidgetArea,
            Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        for area in candidates:
            if self._dock_area_to_int(area) == numeric:
                return area

        return Qt.DockWidgetArea.RightDockWidgetArea

    def _save_visual_macro_dock_state(self) -> None:
        """Persist the current Visual Macro dock geometry/state into settings."""
        if self.visual_macro_dock is None:
            return

        dock = self.visual_macro_dock
        geom = dock.geometry()
        state = self._visual_macro_dock_settings()

        state["visible"] = dock.isVisible()
        state["floating"] = dock.isFloating()
        state["x"] = geom.x()
        state["y"] = geom.y()
        state["width"] = max(geom.width(), 640)
        state["height"] = max(geom.height(), 480)
        state["area"] = self._dock_area_to_int(self.dockWidgetArea(dock))

    def _restore_visual_macro_dock_state(self) -> None:
        """Restore the Visual Macro dock geometry/state from settings."""
        self._visual_macro_restore_scheduled = False

        if self.visual_macro_dock is None:
            return

        dock = self.visual_macro_dock
        state = self._visual_macro_dock_settings()

        # 初回起動など、保存状態がまだなければ既定値で開く
        if not state:
            self._show_visual_macro_editor_default()
            return

        visible = bool(state.get("visible", True))
        floating = bool(state.get("floating", True))
        x = int(state.get("x", self.x() + 80))
        y = int(state.get("y", self.y() + 60))
        width = max(int(state.get("width", 1200)), 640)
        height = max(int(state.get("height", 800)), 480)
        area = self._int_to_dock_area(state.get("area"))

        if floating:
            dock.setFloating(True)
            dock.resize(width, height)
            dock.move(x, y)
        else:
            dock.setFloating(False)
            self.addDockWidget(area, dock)
            dock.resize(width, height)

        if visible:
            dock.show()
            dock.raise_()
        else:
            dock.hide()

    def _show_visual_macro_editor_default(self) -> None:
        """Show the Visual Macro dock with a sensible default layout."""
        if self.visual_macro_dock is None:
            return

        dock = self.visual_macro_dock
        dock.setFloating(True)
        dock.resize(1200, 800)
        dock.move(self.x() + 80, self.y() + 60)
        dock.show()
        dock.raise_()
        dock.activateWindow()

    def _show_visual_macro_editor_initially(self) -> None:
        if self.visual_macro_dock is None:
            return

        dock = self.visual_macro_dock
        dock.setFloating(True)
        dock.resize(1200, 800)

        main_geo = self.geometry()
        x = main_geo.x() + 80
        y = main_geo.y() + 60
        dock.move(x, y)

        dock.show()
        dock.raise_()
        dock.activateWindow()

    def _find_visual_macro_index_by_source_path(self, source_path: str) -> int:
        if self.command_catalog is None:
            return -1

        target = source_path.replace("\\", "/")
        for index, descriptor in enumerate(self.command_catalog.visual_descriptors):
            if descriptor.source_path.replace("\\", "/") == target:
                return index
        return -1

    def _select_visual_macro_by_source_path(self, source_path: str) -> bool:
        index = self._find_visual_macro_index_by_source_path(source_path)
        if index < 0:
            return False

        self.comboBox_VisualMacro.setCurrentIndex(index)
        return True

    def _setup_visual_macro_toggle_action(self) -> None:
        if self.visual_macro_dock is None:
            return

        action = self.visual_macro_dock.toggleViewAction()
        action.setText("Visual Macro Editor")
        action.setShortcut("Ctrl+Shift+V")

        self.visual_macro_toggle_action = action

        view_menu = None
        for menu_action in self.menuBar().actions():
            menu = menu_action.menu()
            if menu is not None and menu.title() in {"表示", "View"}:
                view_menu = menu
                break

        if view_menu is None:
            view_menu = self.menuBar().addMenu("表示")

        view_menu.addAction(action)

    def show_visual_macro_editor(self) -> None:
        if self.visual_macro_dock is None:
            return

        dock = self.visual_macro_dock
        dock.show()
        dock.raise_()
        dock.activateWindow()

    def duplicate_selected_visual_macro(self) -> None:
        self.assign_command()

        descriptor = self.current_visual_descriptor
        if descriptor is None:
            self.logger.error("No Visual Macro is selected.")
            return

        try:
            new_relative_path = self.visual_macro_repository.duplicate_document(
                descriptor.source_path
            )
            self.reload_commands()
            self._select_visual_macro_by_source_path(new_relative_path)
            self.open_selected_visual_macro_in_editor()
            self.logger.info(
                f"Duplicated Visual Macro: {descriptor.source_path} -> {new_relative_path}"
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to duplicate Visual Macro: {exc}")
            QMessageBox.warning(
                self,
                "Visual Macro",
                f"Visual Macro の複製に失敗しました。\n{exc}",
            )

    def new_visual_macro_in_editor(self) -> None:
        if self.visual_macro_editor is None:
            self.logger.error("Visual Macro editor is not available.")
            return

        try:
            self.show_visual_macro_editor()
            self.visual_macro_editor.create_new_document()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to create new Visual Macro document: {exc}")
            QMessageBox.warning(
                self,
                "Visual Macro",
                f"新規 Visual Macro の作成に失敗しました。\n{exc}",
            )

    def delete_selected_visual_macro(self) -> None:
        self.assign_command()

        descriptor = self.current_visual_descriptor
        if descriptor is None:
            self.logger.error("No Visual Macro is selected.")
            return

        try:
            relative_path = self.visual_macro_repository.to_relative_path(
                descriptor.source_path
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to normalize Visual Macro path: {exc}")
            QMessageBox.warning(
                self,
                "Visual Macro",
                f"Visual Macro の削除準備に失敗しました。\n{exc}",
            )
            return

        message = (
            f"'{descriptor.display_name}' を削除しますか？\n\n対象: {relative_path}"
        )
        answer = QMessageBox.question(
            self,
            "Visual Macro",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            if (
                self.visual_macro_editor is not None
                and self.visual_macro_editor.current_document_relative_path
                == relative_path
                and self.visual_macro_editor.is_document_modified
            ):
                QMessageBox.warning(
                    self,
                    "Visual Macro",
                    "現在編集中の Visual Macro に未保存変更があるため、削除できません。",
                )
                return

            deleting_current_editor_file = (
                self.visual_macro_editor is not None
                and self.visual_macro_editor.current_document_relative_path
                == relative_path
            )

            self.visual_macro_repository.delete_document(relative_path)

            if deleting_current_editor_file and self.visual_macro_editor is not None:
                self.show_visual_macro_editor()
                self.visual_macro_editor.create_new_document()

            self.reload_commands()
            self.logger.info(f"Deleted Visual Macro: {relative_path}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to delete Visual Macro: {exc}")
            QMessageBox.warning(
                self,
                "Visual Macro",
                f"Visual Macro の削除に失敗しました。\n{exc}",
            )

    @Slot(bool)
    def _on_visual_macro_visibility_changed(self, visible: bool) -> None:
        if self.visual_macro_toggle_action is not None:
            self.visual_macro_toggle_action.setChecked(visible)

    @Slot(str)
    def on_visual_macro_status_message(self, message: str) -> None:
        self.logger.debug(f"[VisualMacro] {message}")

    @Slot(str)
    def on_visual_macro_run_requested(self, program_json: str) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return

        if self._visual_macro_run_request_in_flight:
            self.logger.warning(
                "Visual Macro run request ignored: request already in flight."
            )
            return

        # すでに Python-like command が走っている/停止中なら editor からの再実行を拒否
        if self.command_session.state in {
            self.command_session.state.RUNNING_PYTHON,
            self.command_session.state.RUNNING_VISUAL,
            self.command_session.state.STOPPING,
        }:
            self.logger.warning(
                f"Visual Macro run request ignored: session state={self.command_session.state}"
            )
            return

        self._visual_macro_run_request_in_flight = True

        metadata = self._get_visual_macro_document_metadata()
        metadata_name = str(metadata.get("name", "")).strip()

        try:
            visual_macro_class = build_visual_macro_command_class(
                program_json=program_json,
                display_name=metadata_name or "Visual Macro",
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._visual_macro_run_request_in_flight = False
            self.logger.error(f"Failed to build Visual Macro: {exc}")
            QMessageBox.warning(
                self,
                "Visual Macro",
                f"Visual Macro の開始準備に失敗しました。\n{exc}",
            )
            return

        relative_path = self._visual_macro_current_relative_path.strip()
        absolute_path = self._visual_macro_current_path.strip()

        if metadata_name:
            display_name = metadata_name
        elif relative_path:
            display_name = Path(relative_path).name
        else:
            display_name = "Visual Macro (Unsaved)"

        if relative_path:
            command_id = f"visual:{relative_path.replace(os.sep, '/')}"
            source_path = absolute_path if absolute_path else relative_path
        else:
            command_id = "visual:unsaved:current"
            source_path = "<unsaved>"

        context = CommandExecutionContext(
            command_id=command_id,
            kind="visual",
            display_name=display_name,
            source_path=source_path,
            trigger_source=CommandTriggerSource.VISUAL_EDITOR.value,
            payload_json=program_json,
        )

        self._visual_macro_command_class = visual_macro_class
        self.current_python_descriptor = None
        self.current_descriptor = None
        self.py_cur_command = visual_macro_class
        self.cur_command = visual_macro_class
        self.command_mode = "python"

        started = self.command_session.start_visual_command(
            visual_macro_class,
            context,
        )
        if not started:
            self._visual_macro_run_request_in_flight = False
            self.logger.error("Visual Macro start request was rejected.")

    @Slot()
    def on_visual_macro_stop_requested(self) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return
        self.command_session.stop_python_command(block=False)

    @Slot(str, bool)
    def on_visual_macro_document_state_changed(
        self,
        relative_path: str,
        modified: bool,
    ) -> None:
        self._visual_macro_current_relative_path = relative_path
        self._visual_macro_is_modified = modified

        if self.visual_macro_editor is not None:
            self._visual_macro_current_path = (
                self.visual_macro_editor.current_document_path
            )
        else:
            self._visual_macro_current_path = ""

        self._sync_visual_macro_combo_from_editor(relative_path)
        self._update_visual_macro_dock_title()

    def _update_visual_macro_dock_title(self) -> None:
        if self.visual_macro_dock is None:
            return

        metadata = self._get_visual_macro_document_metadata()
        metadata_name = str(metadata.get("name", "")).strip()

        if metadata_name:
            title_name = metadata_name
        elif self._visual_macro_current_relative_path:
            title_name = Path(self._visual_macro_current_relative_path).name
        else:
            title_name = "Untitled"

        suffix = " *" if self._visual_macro_is_modified else ""
        self.visual_macro_dock.setWindowTitle(f"Visual Macro - {title_name}{suffix}")

    def _confirm_close_visual_macro_if_modified(self) -> bool:
        """Ask the user what to do if the Visual Macro document has unsaved changes."""
        editor = self.visual_macro_editor
        if editor is None:
            return True

        if not editor.is_document_modified:
            return True

        if editor.current_document_relative_path:
            document_name = Path(editor.current_document_relative_path).name
        else:
            document_name = "Untitled"

        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle("Visual Macro")
        message_box.setText(
            f"Visual Macro '{document_name}' には未保存の変更があります。"
        )
        message_box.setInformativeText("保存してから終了しますか？")

        save_button = message_box.addButton(
            "保存して終了", QMessageBox.ButtonRole.AcceptRole
        )
        discard_button = message_box.addButton(
            "保存せず終了",
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_button = message_box.addButton(QMessageBox.StandardButton.Cancel)

        message_box.setDefaultButton(save_button)
        message_box.exec()

        clicked = message_box.clickedButton()

        if clicked is cancel_button:
            return False

        if clicked is discard_button:
            return True

        save_result = editor.save_current_document_interactive()
        if save_result is True:
            return True

        if save_result is None:
            return False

        QMessageBox.warning(
            self,
            "Visual Macro",
            "Visual Macro の保存に失敗したため、終了を中止しました。",
        )
        return False

    def _get_visual_macro_document_metadata(self) -> dict[str, object]:
        """Return metadata from the current Visual Macro document."""
        editor = self.visual_macro_editor
        if editor is None:
            return {}

        try:
            document_json = editor.collect_document_json()
            if not document_json:
                return {}

            raw_value = json.loads(document_json)
            if not isinstance(raw_value, dict):
                return {}

            metadata = raw_value.get("metadata", {})
            return metadata if isinstance(metadata, dict) else {}
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.debug(f"Failed to collect Visual Macro metadata: {exc}")
            return {}

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

        self.comboBox_VisualMacro.currentIndexChanged.connect(self.assign_command)
        self.comboBox_VisualMacro.currentIndexChanged.connect(
            self.assign_visual_macro_command_to_setting
        )

        self.pushButton_VisualMacroStart.pressed.connect(
            self.start_visual_catalog_command
        )
        self.pushButton_VisualMacroStop.pressed.connect(
            lambda: self.stop_command(block=False)
        )
        self.pushButton_VisualMacroOpen.pressed.connect(
            self.open_selected_visual_macro_in_editor
        )
        self.pushButton_VisualMacroReload.clicked.connect(self.reload_commands)
        self.toolButton_OpenVisualMacroDir.clicked.connect(self.open_visual_macro_dir)
        self.pushButton_VisualMacroNew.pressed.connect(self.new_visual_macro_in_editor)
        self.pushButton_VisualMacroDuplicate.pressed.connect(
            self.duplicate_selected_visual_macro
        )
        self.pushButton_VisualMacroDelete.pressed.connect(
            self.delete_selected_visual_macro
        )
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
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        settings["main_window"]["must"]["fps"] = self.lineEditFPS.text()

    def assign_camera_id_to_setting(self) -> None:
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        settings["main_window"]["must"]["camera_id"] = self.lineEditCameraID.text()

    def assign_com_port_to_setting(self) -> None:
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        settings["main_window"]["must"]["com_port"] = self.lineEditComPort.text()

    def assign_window_size_to_setting(self) -> None:
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        settings["main_window"]["option"]["window_size_width"] = self.width()
        settings["main_window"]["option"]["window_size_height"] = self.height()

    def assign_mcu_command_to_setting(self) -> None:
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        settings["command"]["mcu_command"] = self.comboBox_MCU.itemText(
            self.comboBox_MCU.currentIndex()
        )

    def assign_py_command_to_setting(self) -> None:
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        settings["command"]["py_command"] = self.comboBoxPython.itemText(
            self.comboBoxPython.currentIndex()
        )

    def assign_visual_macro_command_to_setting(self) -> None:
        if self._syncing_visual_macro_selection:
            return

        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        settings["command"]["visual_macro_command"] = (
            self.comboBox_VisualMacro.itemText(self.comboBox_VisualMacro.currentIndex())
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
    # device controls
    # ------------------------------------------------------------------
    def activate_serial(self) -> None:
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        self.request_serial_close.emit()
        self.request_serial_open.emit(settings["main_window"]["must"]["com_port"], "")

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
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")
        try:
            self.request_capture_set_fps.emit(
                int(settings["main_window"]["must"]["fps"])
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
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        enabled = self.actionShow_Serial.isChecked()
        settings["main_window"]["option"]["show_serial"] = enabled
        self.is_show_serial = enabled
        self.request_serial_show.emit(enabled)

    # ------------------------------------------------------------------
    # commands
    # ------------------------------------------------------------------
    def load_commands(self) -> None:
        self.command_catalog = CommandCatalog()
        self.command_catalog.load()

        self._log_loader_errors(self.command_catalog.python_errors)
        self._log_loader_errors(self.command_catalog.mcu_errors)

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
        self.comboBox_VisualMacro.clear()

        if self.command_catalog is None:
            return

        for index, descriptor in enumerate(self.command_catalog.python_descriptors):
            self.comboBoxPython.addItem(descriptor.display_name)

            if descriptor.tooltip is not None:
                self.comboBoxPython.setItemData(
                    index,
                    descriptor.tooltip,
                    Qt.ItemDataRole.ToolTipRole,
                )

            if descriptor.foreground is not None:
                self.comboBoxPython.setItemData(
                    index,
                    descriptor.foreground,
                    QtCore.Qt.ItemDataRole.ForegroundRole,
                )

        for index, descriptor in enumerate(self.command_catalog.visual_descriptors):
            self.comboBox_VisualMacro.addItem(descriptor.display_name)
            if descriptor.tooltip is not None:
                self.comboBox_VisualMacro.setItemData(
                    index,
                    descriptor.tooltip,
                    Qt.ItemDataRole.ToolTipRole,
                )
            if descriptor.foreground is not None:
                self.comboBox_VisualMacro.setItemData(
                    index,
                    descriptor.foreground,
                    Qt.ItemDataRole.ForegroundRole,
                )

        if self.comboBox_VisualMacro.count() > 0:
            self.comboBox_VisualMacro.setCurrentIndex(0)

        for descriptor in self.command_catalog.mcu_descriptors:
            self.comboBox_MCU.addItem(descriptor.display_name)

        if self.comboBoxPython.count() > 0:
            self.comboBoxPython.setCurrentIndex(0)
        if self.comboBox_MCU.count() > 0:
            self.comboBox_MCU.setCurrentIndex(0)

    def assign_command(self) -> None:
        if self.command_catalog is None:
            self.current_python_descriptor = None
            self.current_mcu_descriptor = None
            self.current_visual_descriptor = None
            self.current_descriptor = None
            self.py_cur_command = None
            self.mcu_cur_command = None
            self.cur_command = None
            return

        self.current_python_descriptor = self.command_catalog.get_python_descriptor(
            self.comboBoxPython.currentIndex()
        )
        self.current_mcu_descriptor = self.command_catalog.get_mcu_descriptor(
            self.comboBox_MCU.currentIndex()
        )

        self.current_visual_descriptor = self.command_catalog.get_visual_descriptor(
            self.comboBox_VisualMacro.currentIndex()
        )

        self.py_cur_command = (
            self.current_python_descriptor.command_class
            if self.current_python_descriptor is not None
            else None
        )
        self.mcu_cur_command = (
            self.current_mcu_descriptor.command_class
            if self.current_mcu_descriptor is not None
            else None
        )

        current_tab = self.tabWidget.currentIndex()

        if current_tab == 0:
            self.current_descriptor = self.current_python_descriptor
            self.cur_command = (
                self.current_python_descriptor.command_class
                if self.current_python_descriptor is not None
                else None
            )
        elif current_tab == 1:
            self.current_descriptor = self.current_visual_descriptor
            self.cur_command = None
        elif current_tab == 2:
            self.current_descriptor = self.current_mcu_descriptor
            self.cur_command = (
                self.current_mcu_descriptor.command_class
                if self.current_mcu_descriptor is not None
                else None
            )
        else:
            self.current_descriptor = None
            self.cur_command = None

    def _sync_command_buttons(self) -> None:
        if self.command_session is None:
            python_running = (
                self.command_runtime is not None and self.command_runtime.is_running()
            )
            mcu_running = False
        else:
            python_running = self.command_session.is_python_running()
            mcu_running = self.command_session.is_mcu_running()

        self.pushButton_PythonStart.setEnabled(not python_running)
        self.pushButton_PythonStop.setEnabled(python_running)

        self.pushButton_VisualMacroStart.setEnabled(not python_running)
        self.pushButton_VisualMacroStop.setEnabled(python_running)

        self.pushButton_MCUStart.setEnabled(not mcu_running)
        self.pushButton_MCUStop.setEnabled(mcu_running)

    def set_command_mode(self) -> None:
        current_tab = self.tabWidget.currentIndex()

        if current_tab == 0:
            self.command_mode = "python"
        elif current_tab == 1:
            self.command_mode = "visual"
        elif current_tab == 2:
            self.command_mode = "mcu"
        else:
            raise Exception("Unknown command mode")

    def start_command(self) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return

        self.assign_command()

        if self.current_python_descriptor is None:
            self.logger.error("No Python command is selected.")
            return

        context = CommandExecutionContext(
            command_id=self.current_python_descriptor.command_id,
            kind=self.current_python_descriptor.kind.value,
            display_name=self.current_python_descriptor.display_name,
            source_path=self.current_python_descriptor.source_path,
            trigger_source=CommandTriggerSource.UI_COMBO.value,
        )

        started = self.command_session.start_python_command(
            self.current_python_descriptor.command_class,
            context,
        )
        if started:
            self.command_mode = "python"
            self.cur_command = self.current_python_descriptor.command_class
            self.py_cur_command = self.current_python_descriptor.command_class

    def stop_command(self, block: bool = False) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return
        self.command_session.stop_python_command(block=block)

    def on_command_started(self, name: str) -> None:
        self._visual_macro_run_request_in_flight = False

        if self.command_session is not None:
            self.command_session.on_python_started(name)
        else:
            self.logger.info(f"Command started: {name}")

    def on_command_stopped(self, result: bool) -> None:
        if self.command_session is not None:
            self.command_session.on_python_stopped(result)
        else:
            self.request_gamepad_pause.emit(False)
            self.request_capture_frame_stream.emit(False)
            self._sync_command_buttons()

    def start_mcu_command(self) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return

        self.assign_command()

        if self.current_mcu_descriptor is None:
            self.logger.error("No MCU command is selected.")
            return

        context = CommandExecutionContext(
            command_id=self.current_mcu_descriptor.command_id,
            kind=self.current_mcu_descriptor.kind.value,
            display_name=self.current_mcu_descriptor.display_name,
            source_path=self.current_mcu_descriptor.source_path,
            trigger_source=CommandTriggerSource.UI_COMBO.value,
        )

        started = self.command_session.start_mcu_command(
            self.current_mcu_descriptor.command_class,
            context,
        )
        if started:
            self.command_mode = "mcu"
            self.cur_command = self.current_mcu_descriptor.command_class
            self.mcu_cur_command = self.current_mcu_descriptor.command_class

    def stop_mcu_command(self) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return
        self.command_session.stop_mcu_command()

    @Slot(str)
    def play_mcu(self, s: str) -> None:
        self.request_serial_write.emit(s, False)

    def reload_commands(self) -> None:
        self.stop_command(block=True)

        old_val_mcu = self.comboBox_MCU.itemText(self.comboBox_MCU.currentIndex())
        old_val_py = self.comboBoxPython.itemText(self.comboBoxPython.currentIndex())

        old_visual_source_path = (
            self.current_visual_descriptor.source_path
            if self.current_visual_descriptor is not None
            else ""
        )

        if self.command_catalog is None:
            self.command_catalog = CommandCatalog()
            self.command_catalog.load()
        else:
            self.command_catalog.reload()

        self.set_command_items()

        if self.command_catalog is not None:
            mcu_idx = self.command_catalog.find_mcu_index_by_name(old_val_mcu)
            if mcu_idx != -1:
                self.comboBox_MCU.setCurrentIndex(mcu_idx)
            elif self.comboBox_MCU.count() > 0:
                self.comboBox_MCU.setCurrentIndex(0)

            py_idx = self.command_catalog.find_python_index_by_name(old_val_py)
            if py_idx != -1:
                self.comboBoxPython.setCurrentIndex(py_idx)
            elif self.comboBoxPython.count() > 0:
                self.comboBoxPython.setCurrentIndex(0)

        if old_visual_source_path:
            visual_idx = self._find_visual_macro_combo_index_by_source_path(
                old_visual_source_path
            )
            if visual_idx != -1:
                self.comboBox_VisualMacro.setCurrentIndex(visual_idx)
            elif self.comboBox_VisualMacro.count() > 0:
                self.comboBox_VisualMacro.setCurrentIndex(0)
        elif self.comboBox_VisualMacro.count() > 0:
            self.comboBox_VisualMacro.setCurrentIndex(0)

        self.assign_command()

        if self.command_catalog is not None:
            if (
                not self.command_catalog.python_errors
                and not self.command_catalog.mcu_errors
            ):
                self.logger.info("Reloaded commands.")
            else:
                self._log_loader_errors(self.command_catalog.python_errors)
                self._log_loader_errors(self.command_catalog.mcu_errors)

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
        self,
        left_horizontal: float,
        left_vertical: float,
        right_horizontal: float,
        right_vertical: float,
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
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        enabled = bool(settings["key_config"]["joystick"]["direction"]["LStick"])
        self.request_gamepad_set_l_stick.emit(enabled)

    def gamepad_r_stick(self) -> None:
        settings = self.setting.setting
        if settings is None:
            raise RuntimeError("Settings are not loaded.")

        enabled = bool(settings["key_config"]["joystick"]["direction"]["RStick"])
        self.request_gamepad_set_r_stick.emit(enabled)

    # ------------------------------------------------------------------
    # image / logging / utility
    # ------------------------------------------------------------------

    @Slot(str, int)
    def callback_string_to_log(self, s: str, level: int) -> None:
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

        if not self._confirm_close_visual_macro_if_modified():
            event.ignore()
            return

        if self.preview_timer is not None:
            self.preview_timer.stop()

        settings["main_window"]["option"]["window_showMaximized"] = self.isMaximized()
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

        # 8. Visual Macro dock 状態保存
        self._save_visual_macro_dock_state()

        # 9. 設定保存
        self.assign_visual_macro_command_to_setting()
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
