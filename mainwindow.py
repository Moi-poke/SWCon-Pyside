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
from libs.slot_manager import SlotManager
from libs.template_match_support import TemplateMatchSupport
from libs.Utility import ospath
from libs.visual_macro.editor_widget import VisualMacroEditorWidget
from libs.visual_macro.factory import build_visual_macro_command_class
from libs.visual_macro.repository import VisualMacroRepository
from ui.main_ui import Ui_MainWindow
from ui.QtextLogger import QPlainTextEditLogger

VERSION = "0.9.2 (beta)"
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
        self.slot_manager: Optional[SlotManager] = None
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

        py_cmd = settings["command"]["py_command"]
        mcu_cmd = settings["command"]["mcu_command"]
        visual_cmd = settings["command"]["visual_macro_command"]

        self.connect_slot_manager()
        self.setup_multi_slot_view()
        self.connect_gamepad()
        self.setup_visual_macro_editor()

        self.load_commands()
        self.show_serial()

        try:
            self.comboBoxPython.blockSignals(True)
            self.comboBox_MCU.blockSignals(True)
            self.comboBox_VisualMacro.blockSignals(True)

            mcu_idx = self.comboBox_MCU.findText(mcu_cmd)
            if mcu_idx >= 0:
                self.comboBox_MCU.setCurrentIndex(mcu_idx)

            py_idx = self.comboBoxPython.findText(py_cmd)
            if py_idx >= 0:
                self.comboBoxPython.setCurrentIndex(py_idx)

            visual_idx = self.comboBox_VisualMacro.findText(visual_cmd)
            if visual_idx >= 0:
                self.comboBox_VisualMacro.setCurrentIndex(visual_idx)

        except Exception:
            self.logger.debug("There seems to have been a change in the script.")
        finally:
            self.comboBoxPython.blockSignals(False)
            self.comboBox_MCU.blockSignals(False)
            self.comboBox_VisualMacro.blockSignals(False)

        # Manually sync after unblocking
        self.assign_command()
        self.assign_py_command_to_setting()
        self.assign_mcu_command_to_setting()
        self.assign_visual_macro_command_to_setting()

        # Tell the editor to open the last-used Visual Macro document
        if (
            self.current_visual_descriptor is not None
            and self.visual_macro_editor is not None
        ):
            try:
                startup_path = self.visual_macro_repository.to_relative_path(
                    self.current_visual_descriptor.source_path
                )
                self.visual_macro_editor.set_startup_document_path(startup_path)
            except Exception:
                pass

        self._init_camera_name_list()

        # if self.camera_list:
        #     target_id = str(settings["main_window"]["must"]["camera_id"])
        #     for i, cam in enumerate(self.camera_list):
        #         if str(cam["index"]) == target_id:
        #             self.comboBoxCameraNames.setCurrentIndex(i)
        #             break
        self._sync_old_ui_from_active_slot()

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
        if hasattr(self, "multi_slot_view"):
            self.multi_slot_view.set_camera_list_all(self.camera_list)
        if self.slot_manager is not None:
            self.multi_slot_view.sync_slot_devices(self.slot_manager.slots)

    # ------------------------------------------------------------------
    # worker wiring
    # ------------------------------------------------------------------

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

    def connect_slot_manager(self) -> None:
        """SlotManager を生成し、全スロットを起動する."""
        from libs.slot_manager import SlotManager

        # ---- SlotManager 生成 ----
        self.slot_manager = SlotManager(self)
        configs = self.setting.get_slot_configs()
        self.slot_manager.create_slots(configs)

        # ---- SessionController 構築 (各スロット) ----
        def _session_ctrl_kwargs(slot):
            return dict(
                logger=self.logger,
                pause_gamepad=lambda paused: self.request_gamepad_pause.emit(paused),
                set_frame_stream=lambda on: (
                    slot.capture_worker.set_frame_stream_enabled(on)
                ),
                sync_buttons=lambda: self._sync_command_buttons(),
                play_mcu_callback=self.play_mcu,
            )

        self.slot_manager.build_all_session_controllers(_session_ctrl_kwargs)

        # ---- スロット起動 ----
        self.slot_manager.start_all()

        # ---- アクティブスロットの後方互換参照 ----
        active = self.slot_manager.active_slot
        if active is None:
            self.logger.error("No active slot available")
            return

        self.frame_store = active.frame_store
        self.capture_worker = active.capture_worker
        self.capture_thread = active.capture_thread
        self.serial_worker = active.serial_worker
        self.serial_thread = active.serial_thread
        self.command_runtime = active.command_runtime
        self.command_session = active.command_session
        self.gui_stick_store = active.gui_stick_store

        # ---- capture worker 接続 ----
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

        # ---- serial worker 接続 ----
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

        # ---- command runtime 接続 ----
        self.command_runtime.log.connect(
            self.callback_string_to_log, Qt.ConnectionType.QueuedConnection
        )
        self.command_runtime.started.connect(
            self.on_command_started, Qt.ConnectionType.QueuedConnection
        )
        self.command_runtime.stopped.connect(
            self.on_command_stopped, Qt.ConnectionType.QueuedConnection
        )
        if hasattr(self.command_runtime, "highlight_block_requested"):
            self.command_runtime.highlight_block_requested.connect(
                self._on_visual_macro_highlight_requested,
                Qt.ConnectionType.QueuedConnection,
            )
        if hasattr(self.command_runtime, "clear_block_highlight_requested"):
            self.command_runtime.clear_block_highlight_requested.connect(
                self._on_visual_macro_highlight_cleared,
                Qt.ConnectionType.QueuedConnection,
            )

    @Slot()
    def render_latest_preview(self) -> None:
        # image, seq = self.frame_store.get_preview_if_new(self._last_preview_seq)
        # if image is None:
        #     return

        # self._last_preview_seq = seq
        # self.img = image
        # pix = QPixmap.fromImage(image)
        # self.CaptureImageArea.setPixmap(pix)
        self._update_active_frame_img()

    # ------------------------------------------------------------------
    # visual macro
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_visual_macro_highlight_requested(self, block_id: str) -> None:
        if self.visual_macro_editor is None:
            return
        self.visual_macro_editor.bridge.highlight_block_requested.emit(block_id)

    @Slot()
    def _on_visual_macro_highlight_cleared(self) -> None:
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
            # editor が無題状態 — コンボの選択は維持
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
            self._on_visual_macro_run_requested,
            Qt.ConnectionType.QueuedConnection,
        )
        editor.stop_requested.connect(
            self._on_visual_macro_stop_requested,
            Qt.ConnectionType.QueuedConnection,
        )
        editor.status_message.connect(
            self._on_visual_macro_status_message,
            Qt.ConnectionType.QueuedConnection,
        )

        # すでに入れているならそのまま使ってOK
        if hasattr(self, "_setup_visual_macro_toggle_action"):
            self._setup_visual_macro_toggle_action()

        editor.document_state_changed.connect(
            self._on_visual_macro_document_state_changed,
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
    def _on_visual_macro_status_message(self, message: str) -> None:
        self.logger.debug(f"[VisualMacro] {message}")

    @Slot(str)
    def _on_visual_macro_run_requested(self, program_json: str) -> None:
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
    def _on_visual_macro_stop_requested(self) -> None:
        if self.command_session is None:
            self.logger.error("Command session controller is not ready.")
            return
        self.command_session.stop_python_command(block=False)

    @Slot(str, bool)
    def _on_visual_macro_document_state_changed(
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
            # lambda: self.reconnect_camera(self.lineEditCameraID.text())
            self._on_reload_camera_for_active_slot
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
        self.pushButtonReloadPort.clicked.connect(
            # self.activate_serial
            self._on_reload_port_for_active_slot
        )

        self.pushButtonScreenShot.clicked.connect(self.screen_shot)
        self.toolButtonOpenScreenShotDir.clicked.connect(self.open_screen_shot_dir)
        self.toolButtonOpenPythonDir.clicked.connect(self.open_python_shot_dir)
        self.toolButton_OpenMCUDir.clicked.connect(self.open_mcu_shot_dir)
        self.comboBoxCameraNames.currentIndexChanged.connect(
            # self.handle_camera_selection_changed
            self._on_camera_combo_changed_for_active_slot
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
        self.comboBoxPython.blockSignals(True)
        self.comboBox_MCU.blockSignals(True)
        self.comboBox_VisualMacro.blockSignals(True)
        try:
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

            for descriptor in self.command_catalog.mcu_descriptors:
                self.comboBox_MCU.addItem(descriptor.display_name)

            if self.comboBoxPython.count() > 0:
                self.comboBoxPython.setCurrentIndex(0)
            if self.comboBox_MCU.count() > 0:
                self.comboBox_MCU.setCurrentIndex(0)
            if self.comboBox_VisualMacro.count() > 0:
                self.comboBox_VisualMacro.setCurrentIndex(0)
        finally:
            self.comboBoxPython.blockSignals(False)
            self.comboBox_MCU.blockSignals(False)
            self.comboBox_VisualMacro.blockSignals(False)

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

        self.comboBoxPython.blockSignals(True)
        self.comboBox_MCU.blockSignals(True)
        self.comboBox_VisualMacro.blockSignals(True)
        try:
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

        finally:
            self.comboBoxPython.blockSignals(False)
            self.comboBox_MCU.blockSignals(False)
            self.comboBox_VisualMacro.blockSignals(False)

        self.assign_command()
        self.assign_py_command_to_setting()
        self.assign_mcu_command_to_setting()
        self.assign_visual_macro_command_to_setting()

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

    # ---
    # Multi Slot
    # ---

    # ------------------------------------------------------------------
    # アクティブスロット切替
    # ------------------------------------------------------------------

    @Slot(int)
    def _on_multi_slot_active_changed(self, slot_id: int) -> None:
        """パネルクリックによるアクティブスロットの切替."""
        if self.slot_manager is None:
            return

        self.slot_manager.set_active_slot(slot_id)
        active = self.slot_manager.active_slot
        if active is None:
            return

        # 後方互換参照の再配線
        self.frame_store = active.frame_store
        self.capture_worker = active.capture_worker
        self.capture_thread = active.capture_thread
        self.serial_worker = active.serial_worker
        self.serial_thread = active.serial_thread
        self.command_runtime = active.command_runtime
        self.command_session = active.command_session
        self.gui_stick_store = active.gui_stick_store

        # 旧UIの表示をアクティブスロットに同期
        self._sync_old_ui_from_active_slot()

        # ゲームパッドルーティング先を更新
        self._sync_command_buttons()

        # 設定に保存
        settings = self.setting.setting
        if settings is not None:
            settings["active_gamepad_slot"] = slot_id

        self.logger.debug(f"Active slot changed to {slot_id}")

    # ------------------------------------------------------------------
    # 旧UIとアクティブスロットの同期
    # ------------------------------------------------------------------

    def _sync_old_ui_from_active_slot(self) -> None:
        """旧UIのカメラ/COM/FPS 表示をアクティブスロットの設定に同期する."""
        if self.slot_manager is None:
            return
        active = self.slot_manager.active_slot
        if active is None:
            return

        cfg = active.config

        # カメラID
        self.lineEditCameraID.blockSignals(True)
        self.lineEditCameraID.setText(str(cfg.camera_id))
        self.lineEditCameraID.blockSignals(False)

        # COMポート
        self.lineEditComPort.blockSignals(True)
        self.lineEditComPort.setText(cfg.com_port)
        self.lineEditComPort.blockSignals(False)

        # カメラ名コンボボックス同期
        if hasattr(self, "camera_list") and self.camera_list:
            self.comboBoxCameraNames.blockSignals(True)
            for i, cam in enumerate(self.camera_list):
                if int(cam["index"]) == cfg.camera_id:
                    self.comboBoxCameraNames.setCurrentIndex(i)
                    break
            self.comboBoxCameraNames.blockSignals(False)

    # ------------------------------------------------------------------
    # 旧UIボタンからのカメラ/シリアルリロード
    # ------------------------------------------------------------------

    def _on_reload_camera_for_active_slot(self) -> None:
        """旧UIの「カメラ再読み込み」ボタン → アクティブスロットのカメラを再オープン."""
        if self.slot_manager is None:
            return
        active = self.slot_manager.active_slot
        if active is None:
            return

        try:
            camera_id = int(self.lineEditCameraID.text())
        except (ValueError, TypeError):
            self.logger.error(f"Invalid camera id: {self.lineEditCameraID.text()}")
            return

        active.reopen_camera(camera_id)
        self.logger.info(f"Slot {active.slot_id}: camera reloaded to {camera_id}")

        # パネルにも反映
        if hasattr(self, "multi_slot_view"):
            p = self.multi_slot_view.panel(active.slot_id)
            if p is not None:
                p.select_camera(camera_id)

        # 設定保存
        self._save_current_slot_configs()

    def _on_reload_port_for_active_slot(self) -> None:
        """旧UIの「ポート再読み込み」ボタン → アクティブスロットのシリアルを再接続."""
        if self.slot_manager is None:
            return
        active = self.slot_manager.active_slot
        if active is None:
            return

        port = self.lineEditComPort.text().strip()

        active.close_serial()
        if port:
            active.open_serial(port)
        self.logger.info(f"Slot {active.slot_id}: serial reloaded to '{port}'")

        # パネルにも反映
        if hasattr(self, "multi_slot_view"):
            p = self.multi_slot_view.panel(active.slot_id)
            if p is not None:
                p.set_com_port(port)

        # 設定保存
        self._save_current_slot_configs()

    def _on_camera_combo_changed_for_active_slot(self, index: int) -> None:
        """旧UIのカメラ名コンボボックス変更 → アクティブスロットのカメラを変更."""
        if not hasattr(self, "camera_list"):
            return
        if index < 0 or index >= len(self.camera_list):
            return
        if self.slot_manager is None:
            return
        active = self.slot_manager.active_slot
        if active is None:
            return

        cam_index = int(self.camera_list[index]["index"])

        # lineEditCameraID も更新
        self.lineEditCameraID.blockSignals(True)
        self.lineEditCameraID.setText(str(cam_index))
        self.lineEditCameraID.blockSignals(False)

        active.reopen_camera(cam_index)
        self.logger.info(
            f"Slot {active.slot_id}: camera changed to "
            f"{self.camera_list[index]['name']} (index={cam_index})"
        )

        # パネルにも反映
        if hasattr(self, "multi_slot_view"):
            p = self.multi_slot_view.panel(active.slot_id)
            if p is not None:
                p.select_camera(cam_index)

        # 設定保存
        self._save_current_slot_configs()

    # ------------------------------------------------------------------
    # パネルからのコマンド操作
    # ------------------------------------------------------------------

    @Slot(int)
    def _on_multi_slot_start(self, slot_id: int) -> None:
        """パネルの▶ボタンによるコマンド開始."""
        if self.slot_manager is None:
            return

        slot = self.slot_manager.slot(slot_id)
        if slot is None or slot.command_session is None:
            self.logger.error(f"Slot {slot_id}: command session not ready")
            return

        # 現在のPythonタブで選択中のコマンドクラスを使用
        self.assign_command()
        if self.current_python_descriptor is None:
            self.logger.error("No Python command is selected.")
            return

        from libs.command_models import CommandExecutionContext, CommandTriggerSource

        context = CommandExecutionContext(
            command_id=self.current_python_descriptor.command_id,
            kind=self.current_python_descriptor.kind.value,
            display_name=self.current_python_descriptor.display_name,
            source_path=self.current_python_descriptor.source_path,
            trigger_source=CommandTriggerSource.UI_COMBO.value,
        )

        started = slot.command_session.start_python_command(
            self.current_python_descriptor.command_class,
            context,
        )
        if started:
            self.logger.info(
                f"Slot {slot_id}: started {self.current_python_descriptor.display_name}"
            )

    @Slot(int)
    def _on_multi_slot_stop(self, slot_id: int) -> None:
        """パネルの⏹ボタンによるコマンド停止."""
        if self.slot_manager is None:
            return

        slot = self.slot_manager.slot(slot_id)
        if slot is None or slot.command_session is None:
            return

        slot.command_session.stop_python_command(block=False)
        self.logger.info(f"Slot {slot_id}: stop requested")

    # ------------------------------------------------------------------
    # パネルからのデバイス変更
    # ------------------------------------------------------------------

    @Slot(int, int)
    def _on_multi_slot_camera_change(self, slot_id: int, camera_id: int) -> None:
        """パネルのカメラ変更."""
        if self.slot_manager is None:
            return

        slot = self.slot_manager.slot(slot_id)
        if slot is None:
            return

        slot.reopen_camera(camera_id)
        self.logger.info(f"Slot {slot_id}: camera changed to {camera_id}")

        # 設定保存
        self._save_current_slot_configs()

        # アクティブスロットなら旧UIにも反映
        if slot_id == self.slot_manager.active_slot_index:
            self._sync_old_ui_from_active_slot()

    @Slot(int, str)
    def _on_multi_slot_com_change(self, slot_id: int, port: str) -> None:
        """パネルのCOMポート変更."""
        if self.slot_manager is None:
            return

        slot = self.slot_manager.slot(slot_id)
        if slot is None:
            return

        slot.close_serial()
        if port:
            slot.open_serial(port)
        self.logger.info(f"Slot {slot_id}: COM port changed to '{port}'")

        # 設定保存
        self._save_current_slot_configs()

        # アクティブスロットなら旧UIにも反映
        if slot_id == self.slot_manager.active_slot_index:
            self._sync_old_ui_from_active_slot()

    # ------------------------------------------------------------------
    # レイアウト変更
    # ------------------------------------------------------------------

    @Slot(str)
    def _on_multi_slot_layout_changed(self, mode: str) -> None:
        """レイアウト変更を設定に保存する."""
        settings = self.setting.setting
        if settings is not None:
            settings["multi_slot_layout"] = mode
        self.logger.debug(f"Layout changed to {mode}")

    @Slot(int, bool)
    def _on_slot_enabled_changed(self, slot_id: int, enabled: bool) -> None:
        """ツールバーのチェックボックスによるスロット有効/無効切替."""
        if self.slot_manager is None:
            return

        if enabled:
            self.slot_manager.enable_slot(slot_id)
        else:
            self.slot_manager.disable_slot(slot_id)

        # MultiSlotView のレイアウトを再構築
        if hasattr(self, "multi_slot_view"):
            self.multi_slot_view.refresh_enabled_layout()

        # アクティブスロットが無効化された場合、最初の有効スロットに切替
        if not enabled and slot_id == self.slot_manager.active_slot_index:
            enabled_slots = self.slot_manager.enabled_slots
            if enabled_slots:
                new_active = enabled_slots[0].slot_id
                self._on_multi_slot_active_changed(new_active)
                if hasattr(self, "multi_slot_view"):
                    self.multi_slot_view.update_slot_checkbox(
                        slot_id,
                        False,
                    )

        # 設定保存
        self._save_current_slot_configs()
        self.logger.info(f"Slot {slot_id}: {'enabled' if enabled else 'disabled'}")

    # ------------------------------------------------------------------
    # SlotManager シグナル → パネルステータス更新
    # ------------------------------------------------------------------

    @Slot(int, bool, str)
    def _on_slot_serial_state_for_panel(
        self,
        slot_id: int,
        opened: bool,
        label: str,
    ) -> None:
        """スロットのシリアル状態をパネルに反映する."""
        if not hasattr(self, "multi_slot_view"):
            return
        panel = self.multi_slot_view.panel(slot_id)
        if panel is not None:
            panel.set_serial_status(opened, label)

    @Slot(int, str)
    def _on_slot_command_started_for_panel(self, slot_id: int, name: str) -> None:
        """コマンド開始をパネルに反映する."""
        if not hasattr(self, "multi_slot_view"):
            return
        panel = self.multi_slot_view.panel(slot_id)
        if panel is not None:
            panel.set_command_status(running=True, name=name)

    @Slot(int, bool)
    def _on_slot_command_stopped_for_panel(self, slot_id: int, result: bool) -> None:
        """コマンド停止をパネルに反映する."""
        if not hasattr(self, "multi_slot_view"):
            return
        panel = self.multi_slot_view.panel(slot_id)
        if panel is not None:
            panel.set_command_status(running=False)

    # ------------------------------------------------------------------
    # ヘルパー
    # ------------------------------------------------------------------

    def _save_current_slot_configs(self) -> None:
        """現在のスロット設定を settings.toml に保存する."""
        if self.slot_manager is None:
            return

        configs = [s.config for s in self.slot_manager.slots]
        self.setting.save_slot_configs(configs)

    def _update_active_frame_img(self) -> None:
        """後方互換: アクティブスロットの最新フレームを self.img に反映する.

        既存の render_latest_preview を以下に置き換え可能:

            def render_latest_preview(self) -> None:
                self._update_active_frame_img()

        MultiSlotView がプレビュー描画を担当するため、
        self.img (ピクセル座標取得用) の更新のみ行う。
        """
        if self.frame_store is None:
            return

        image, seq = self.frame_store.get_preview_if_new(self._last_preview_seq)
        if image is None:
            return

        self._last_preview_seq = seq
        self.img = image

    def setup_multi_slot_view(self) -> None:
        """MultiSlotView を生成し、既存の CaptureImageArea を置換する.

        呼び出し位置: __init__ 内 — connect_slot_manager() の直後
        """
        import logging
        from PySide6.QtWidgets import QGridLayout, QSizePolicy
        from PySide6.QtCore import Qt
        from libs.multi_slot_view import MultiSlotView

        logger = logging.getLogger(__name__)

        self.multi_slot_view = MultiSlotView(parent=self)
        self.multi_slot_view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        # CaptureImageArea の min/max 制約を引き継がない
        self.multi_slot_view.setMinimumSize(0, 0)
        self.multi_slot_view.setMaximumSize(16777215, 16777215)

        # ---- gridLayout_4 を直接取得 ----
        # main_ui.py (Designer 生成) で CaptureImageArea は
        # gridLayout_4[row=2, col=0] に AlignHCenter|AlignVCenter 付きで配置されている。
        # parent.layout() → gridLayout_7 であり、indexOf(CaptureImageArea) は -1 になる。
        grid4 = self.centralwidget.findChild(QGridLayout, "gridLayout_4")

        if grid4 is not None:
            logger.info(
                "setup_multi_slot_view: Found gridLayout_4, "
                "replacing CaptureImageArea at row=2"
            )

            # 旧ウィジェットを除去
            grid4.removeWidget(self.CaptureImageArea)
            self.CaptureImageArea.hide()
            self.CaptureImageArea.setParent(None)

            # ★ アライメントフラグなしで追加 — セル全体を埋める
            grid4.addWidget(self.multi_slot_view, 2, 0, 1, 1)

            # ★ row=2 にストレッチを設定 — 残り全スペースを割り当て
            grid4.setRowStretch(2, 1)
            # 他の行 (frame_2=row1, frame=row3) はストレッチ 0 のまま → 固定高さ

            logger.info(
                "setup_multi_slot_view: MultiSlotView placed at gridLayout_4[2,0], "
                "rowStretch(2)=1"
            )
        else:
            # フォールバック: gridLayout_4 が見つからない場合
            logger.warning(
                "setup_multi_slot_view: gridLayout_4 not found, "
                "falling back to parent layout replacement"
            )
            parent_widget = self.CaptureImageArea.parentWidget()
            layout = parent_widget.layout() if parent_widget else None

            if layout is not None:
                layout.replaceWidget(self.CaptureImageArea, self.multi_slot_view)
                self.CaptureImageArea.hide()
                self.CaptureImageArea.setParent(None)
            else:
                self.CaptureImageArea.hide()
                self.multi_slot_view.setParent(
                    parent_widget if parent_widget else self,
                )

        # ---- パネル初期化 ----
        if self.slot_manager is not None:
            self.multi_slot_view.setup_panels(
                self.slot_manager.slots,
                self.slot_manager.active_slot_index,
            )

        # ---- カメラ一覧をパネルに反映 ----
        if hasattr(self, "camera_list") and self.camera_list:
            self.multi_slot_view.set_camera_list_all(self.camera_list)
            self.multi_slot_view.sync_slot_devices(self.slot_manager.slots)

        # ---- レイアウト復元 ----
        settings = self.setting.setting
        if settings is not None:
            layout_mode = settings.get("multi_slot_layout", "single")
            self.multi_slot_view.set_layout_mode(layout_mode)

        # ---- MultiSlotView シグナル接続 ----
        self.multi_slot_view.active_slot_changed.connect(
            self._on_multi_slot_active_changed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.multi_slot_view.layout_mode_changed.connect(
            self._on_multi_slot_layout_changed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.multi_slot_view.slot_start_requested.connect(
            self._on_multi_slot_start,
            Qt.ConnectionType.QueuedConnection,
        )
        self.multi_slot_view.slot_stop_requested.connect(
            self._on_multi_slot_stop,
            Qt.ConnectionType.QueuedConnection,
        )
        self.multi_slot_view.camera_change_requested.connect(
            self._on_multi_slot_camera_change,
            Qt.ConnectionType.QueuedConnection,
        )
        self.multi_slot_view.com_port_change_requested.connect(
            self._on_multi_slot_com_change,
            Qt.ConnectionType.QueuedConnection,
        )
        # ---- スロット有効/無効切替 ----
        self.multi_slot_view.slot_enabled_changed.connect(
            self._on_slot_enabled_changed,
            Qt.ConnectionType.QueuedConnection,
        )

        # ---- SlotManager シグナル → パネルステータス更新 ----
        if self.slot_manager is not None:
            self.slot_manager.slot_serial_state_changed.connect(
                self._on_slot_serial_state_for_panel,
                Qt.ConnectionType.QueuedConnection,
            )
            self.slot_manager.slot_command_started.connect(
                self._on_slot_command_started_for_panel,
                Qt.ConnectionType.QueuedConnection,
            )
            self.slot_manager.slot_command_stopped.connect(
                self._on_slot_command_stopped_for_panel,
                Qt.ConnectionType.QueuedConnection,
            )

        # ---- プレビュー開始 ----
        self.multi_slot_view.start_preview()

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
        settings["command"]["visual_macro_command"] = (
            self.comboBox_VisualMacro.currentText()
        )

        if self.template_matching_support_tool is not None:
            self.template_matching_support_tool.close()

        # 1. UIから新規操作を止める
        self.setEnabled(False)

        # 2. command stop
        self.stop_command(block=True)

        # 3. gamepad stop
        self.request_gamepad_pause.emit(True)
        self.request_gamepad_stop.emit()

        # 4-6. slot manager handles capture + serial stop + thread cleanup
        if hasattr(self, "multi_slot_view"):
            self.multi_slot_view.stop_preview()

        if self.slot_manager is not None:
            self.slot_manager.shutdown_all()

        # 7. gamepad thread quit/wait
        if self.gamepad_thread is not None:
            self.gamepad_thread.quit()
            self.gamepad_thread.wait(3000)

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
