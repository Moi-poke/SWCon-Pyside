from __future__ import annotations

import logging
import threading
from typing import Optional, Type

import numpy as np
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from libs.frame_store import FrameStore


class CommandContext:
    def __init__(self, frame_store: FrameStore) -> None:
        self._frame_store = frame_store
        self._stop_event = threading.Event()

    def latest_frame_copy(self) -> Optional[np.ndarray]:
        return self._frame_store.latest_raw_copy()

    def request_stop(self) -> None:
        self._stop_event.set()

    def clear_stop(self) -> None:
        self._stop_event.clear()

    def is_stop_requested(self) -> bool:
        return self._stop_event.is_set()


class CommandThread(QThread):
    log = Signal(str, int)
    serial_input = Signal(object, float, float, object)
    send_serial = Signal(str)
    recognize_rect = Signal(tuple, tuple, object, int)
    command_finished = Signal(bool)

    def __init__(
        self,
        command_cls: Type[QObject],
        context: CommandContext,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._command_cls = command_cls
        self._context = context

    def request_stop(self) -> None:
        self._context.request_stop()

    def run(self) -> None:
        worker = self._command_cls()

        if hasattr(worker, "set_runtime_context"):
            worker.set_runtime_context(self._context)

        worker.print_strings.connect(self.log)
        worker.serial_input.connect(self.serial_input)
        worker.send_serial.connect(self.send_serial)
        worker.recognize_rect.connect(self.recognize_rect)
        worker.stop_function.connect(self.command_finished)

        try:
            if hasattr(worker, "__post_init__"):
                worker.__post_init__()
        except Exception as exc:
            self.log.emit(f"Command __post_init__ failed: {exc}", logging.ERROR)

        worker.run()


class CommandRuntime(QObject):
    log = Signal(str, int)
    started = Signal(str)
    stopped = Signal(bool)

    def __init__(
        self, frame_store: FrameStore, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._context = CommandContext(frame_store)
        self._thread: Optional[CommandThread] = None
        self._pending_result: Optional[bool] = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start(self, command_cls, serial_worker, capture_worker) -> bool:
        if self.is_running():
            self.log.emit("Command is already running.", logging.WARNING)
            return False

        self._context.clear_stop()
        self._pending_result = None
        self._thread = CommandThread(command_cls, self._context, parent=self)

        self._thread.log.connect(self.log.emit, Qt.ConnectionType.QueuedConnection)
        self._thread.serial_input.connect(
            serial_worker.on_keypress, Qt.ConnectionType.QueuedConnection
        )
        self._thread.send_serial.connect(
            serial_worker.write_row, Qt.ConnectionType.QueuedConnection
        )
        self._thread.recognize_rect.connect(
            capture_worker.add_rect, Qt.ConnectionType.QueuedConnection
        )
        self._thread.command_finished.connect(
            self._on_command_finished, Qt.ConnectionType.QueuedConnection
        )
        self._thread.finished.connect(
            self._on_thread_finished, Qt.ConnectionType.QueuedConnection
        )

        self._thread.start()
        self.started.emit(getattr(command_cls, "NAME", command_cls.__name__))
        return True

    def stop(self, block: bool = False, timeout_ms: int = 5000) -> None:
        if not self.is_running():
            return

        self._context.request_stop()

        if block and self._thread is not None:
            finished = self._thread.wait(timeout_ms)
            if not finished:
                self.log.emit(
                    f"Command thread did not stop within {timeout_ms} ms.",
                    logging.WARNING,
                )

    @Slot(bool)
    def _on_command_finished(self, result: bool) -> None:
        self._pending_result = result

    @Slot()
    def _on_thread_finished(self) -> None:
        result = self._pending_result if self._pending_result is not None else False
        self._pending_result = None

        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

        self.stopped.emit(result)
