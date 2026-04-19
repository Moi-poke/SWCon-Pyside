"""SessionSlot - 1台の Switch 操作に必要なリソースを束ねるスロット."""
from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal

from libs.capture import CaptureWorker
from libs.command_runtime import CommandRuntime
from libs.command_session_controller import CommandSessionController
from libs.frame_store import FrameStore
from libs.frame_store_registry import FrameStoreRegistry
from libs.gui_stick_store import GuiStickStore
from libs.keys import KeyPress
from libs.serial_worker import SerialWorker
from libs.slot_config import SlotConfig

logger = logging.getLogger(__name__)


class SessionSlot(QObject):
    """1 スロット = 1 Switch に対応するリソースバンドル."""

    # signals — すべて slot_id を第1引数に含む
    log_message = Signal(int, str, int)
    command_started = Signal(int, str)
    command_stopped = Signal(int, bool)
    serial_state_changed = Signal(int, bool, str)
    highlight_block = Signal(int, str)
    clear_block_highlight = Signal(int)

    def __init__(
        self,
        config: SlotConfig,
        frame_registry: FrameStoreRegistry,
        parent: Optional[QObject] = None,
        use_subprocess: bool = False,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._slot_id = config.slot_id
        self._frame_registry = frame_registry

        # ---- stores ----
        self.frame_store = FrameStore()
        self.gui_stick_store = GuiStickStore()
        frame_registry.register(self._slot_id, self.frame_store)

        # ---- capture ----
        self.capture_thread = QThread(parent)
        self.capture_thread.setObjectName(f"CaptureThread-{self._slot_id}")
        self.capture_worker = CaptureWorker(
            camera_id=config.camera_id,
            fps=config.fps,
            frame_store=self.frame_store,
            use_subprocess=use_subprocess,
        )
        self.capture_worker.moveToThread(self.capture_thread)

        # ---- serial ----
        self.serial_thread = QThread(parent)
        self.serial_thread.setObjectName(f"SerialThread-{self._slot_id}")
        self.serial_worker = SerialWorker(
            is_show_serial=False,
            keypress_factory=KeyPress,
            gui_stick_store=self.gui_stick_store,
        )
        self.serial_worker.moveToThread(self.serial_thread)

        # ---- command runtime ----
        self.command_runtime = CommandRuntime(
            frame_store=self.frame_store,
            frame_registry=self._frame_registry,
            slot_id=self._slot_id,
            parent=parent,
        )

        # ---- session controller (MainWindow 側で build する) ----
        self.command_session: Optional[CommandSessionController] = None

        # ---- state ----
        self._serial_open: bool = False

        # ---- signal wiring ----
        self._wire_signals()

    # ================================================================
    # Properties
    # ================================================================

    @property
    def slot_id(self) -> int:
        return self._slot_id

    @property
    def config(self) -> SlotConfig:
        return self._config

    @config.setter
    def config(self, value: SlotConfig) -> None:
        self._config = value

    @property
    def is_serial_open(self) -> bool:
        return self._serial_open

    # ================================================================
    # Lifecycle
    # ================================================================

    def build_session_controller(self, **extra_callbacks: Any) -> None:
        """CommandSessionController を構築する."""
        self.command_session = CommandSessionController(
            command_runtime=self.command_runtime,
            serial_worker=self.serial_worker,
            capture_worker=self.capture_worker,
            **extra_callbacks,
        )

    def start(self) -> None:
        """スレッドを起動する."""
        self.capture_thread.started.connect(self.capture_worker.start_capture)
        self.capture_thread.finished.connect(self.capture_worker.deleteLater)

        self.serial_thread.started.connect(self.serial_worker.start)
        self.serial_thread.finished.connect(self.serial_worker.deleteLater)

        self.capture_thread.start()
        self.serial_thread.start()

        if self._config.com_port:
            self.open_serial(self._config.com_port)

    def shutdown(self, timeout_ms: int = 3000) -> None:
        """全リソースを安全に停止する."""
        logger.info("Slot %d: shutting down ...", self._slot_id)
        if self.command_session is not None:
            try:
                self.command_session.stop_all()
            except Exception:
                pass
        try:
            self.capture_worker.stop_capture()
        except Exception:
            pass
        try:
            self.serial_worker.close_port()
        except Exception:
            pass
        self._frame_registry.unregister(self._slot_id)
        for thread in (self.capture_thread, self.serial_thread):
            thread.quit()
            if not thread.wait(timeout_ms):
                logger.warning(
                    "Slot %d: thread %s did not quit in %d ms",
                    self._slot_id, thread.objectName(), timeout_ms,
                )

    # ================================================================
    # Camera
    # ================================================================

    def reopen_camera(self, camera_id: int) -> None:
        self._config.camera_id = camera_id
        self.capture_worker.reopen_camera(camera_id)

    def set_fps(self, fps: int) -> None:
        self._config.fps = fps
        self.capture_worker.set_fps(fps)

    # ================================================================
    # Serial
    # ================================================================

    def open_serial(self, port: str) -> None:
        self._config.com_port = port
        self.serial_worker.open_port(port)

    def close_serial(self) -> None:
        self.serial_worker.close_port()

    # ================================================================
    # Internal — signal wiring
    # ================================================================

    def _wire_signals(self) -> None:
        sid = self._slot_id

        rt = self.command_runtime
        if hasattr(rt, "log"):
            rt.log.connect(
                lambda msg, lvl, _s=sid: self.log_message.emit(_s, msg, lvl),
                Qt.ConnectionType.QueuedConnection,
            )
        if hasattr(rt, "started"):
            rt.started.connect(
                lambda name, _s=sid: self.command_started.emit(_s, name),
                Qt.ConnectionType.QueuedConnection,
            )
        if hasattr(rt, "stopped"):
            rt.stopped.connect(
                lambda result, _s=sid: self.command_stopped.emit(_s, result),
                Qt.ConnectionType.QueuedConnection,
            )
        if hasattr(rt, "highlight_block_requested"):
            rt.highlight_block_requested.connect(
                lambda bid, _s=sid: self.highlight_block.emit(_s, bid),
                Qt.ConnectionType.QueuedConnection,
            )
        if hasattr(rt, "clear_block_highlight_requested"):
            rt.clear_block_highlight_requested.connect(
                lambda _s=sid: self.clear_block_highlight.emit(_s),
                Qt.ConnectionType.QueuedConnection,
            )

        sw = self.serial_worker
        if hasattr(sw, "serial_state_changed"):
            sw.serial_state_changed.connect(
                lambda opened, label, _s=sid: self._on_serial_state(
                    _s, opened, label
                ),
                Qt.ConnectionType.QueuedConnection,
            )
        if hasattr(sw, "log"):
            sw.log.connect(
                lambda msg, lvl, _s=sid: self.log_message.emit(_s, msg, lvl),
                Qt.ConnectionType.QueuedConnection,
            )

        cw = self.capture_worker
        if hasattr(cw, "log"):
            cw.log.connect(
                lambda msg, lvl, _s=sid: self.log_message.emit(_s, msg, lvl),
                Qt.ConnectionType.QueuedConnection,
            )

    def _on_serial_state(
        self, slot_id: int, opened: bool, label: str
    ) -> None:
        self._serial_open = opened
        self.serial_state_changed.emit(slot_id, opened, label)
