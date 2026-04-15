"""Session controller for Python / Visual Macro / MCU command execution (core version)."""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Callable, Optional

from PySide6.QtCore import Qt

from libs.CommandBase import CommandBase
from libs.command_models import CommandExecutionContext
from libs.command_runtime import CommandRuntime
from libs.capture import CaptureWorker
from libs.mcu_command_base import McuCommand
from libs.serial_worker import SerialWorker


class CommandExecutionState(Enum):
    """High-level command execution state."""

    IDLE = auto()
    RUNNING_PYTHON = auto()
    RUNNING_VISUAL = auto()
    RUNNING_MCU = auto()
    STOPPING = auto()


class CommandSessionController:
    """Coordinate command execution lifecycle outside MainWindow."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        command_runtime: CommandRuntime,
        serial_worker: Optional[SerialWorker],
        capture_worker: Optional[CaptureWorker],
        pause_gamepad: Callable[[bool], None],
        set_frame_stream: Callable[[bool], None],
        sync_buttons: Callable[[], None],
        play_mcu_callback: Callable[[str], None],
    ) -> None:
        self._logger = logger
        self._command_runtime = command_runtime
        self._serial_worker = serial_worker
        self._capture_worker = capture_worker
        self._pause_gamepad = pause_gamepad
        self._set_frame_stream = set_frame_stream
        self._sync_buttons = sync_buttons
        self._play_mcu_callback = play_mcu_callback

        self._state = CommandExecutionState.IDLE
        self._current_python_command_class: Optional[type[CommandBase]] = None
        self._current_mcu_command_class: Optional[type[McuCommand]] = None
        self._mcu_command: Optional[McuCommand] = None
        self._active_python_context: Optional[CommandExecutionContext] = None
        self._active_mcu_context: Optional[CommandExecutionContext] = None

    @property
    def state(self) -> CommandExecutionState:
        return self._state

    def is_python_running(self) -> bool:
        return self._command_runtime.is_running()

    def is_mcu_running(self) -> bool:
        return self._mcu_command is not None

    def start_python_command(self, command_class: type[CommandBase], context: CommandExecutionContext) -> bool:
        return self._start_python_like_command(command_class=command_class, context=context, visual=False)

    def start_visual_command(self, command_class: type[CommandBase], context: CommandExecutionContext) -> bool:
        return self._start_python_like_command(command_class=command_class, context=context, visual=True)

    def _start_python_like_command(
        self,
        *,
        command_class: type[CommandBase],
        context: CommandExecutionContext,
        visual: bool,
    ) -> bool:
        if self._serial_worker is None or self._capture_worker is None:
            self._logger.error("Command runtime dependencies are not ready.")
            self._sync_buttons()
            return False

        self.stop_all(block=True)

        self._pause_gamepad(True)
        self._set_frame_stream(True)

        self._current_python_command_class = command_class
        self._active_python_context = context
        self._state = CommandExecutionState.RUNNING_VISUAL if visual else CommandExecutionState.RUNNING_PYTHON

        started = self._command_runtime.start(command_class, self._serial_worker, self._capture_worker)
        if not started:
            self._logger.error("Failed to start Python-like command.")
            self._pause_gamepad(False)
            self._set_frame_stream(False)
            self._active_python_context = None
            self._state = CommandExecutionState.RUNNING_MCU if self._mcu_command is not None else CommandExecutionState.IDLE
            self._sync_buttons()
            return False

        self._sync_buttons()
        return True

    def stop_python_command(self, *, block: bool) -> None:
        if not self._command_runtime.is_running():
            self._set_frame_stream(False)
            self._state = CommandExecutionState.RUNNING_MCU if self._mcu_command is not None else CommandExecutionState.IDLE
            self._sync_buttons()
            return

        self._logger.debug("Send stop request to command runtime.")
        self._state = CommandExecutionState.STOPPING
        self._command_runtime.stop(block=block)
        self._set_frame_stream(False)
        self._sync_buttons()

    def start_mcu_command(self, command_class: type[McuCommand], context: CommandExecutionContext) -> bool:
        self.stop_all(block=True)

        try:
            mcu_command = command_class()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error(f"Failed to instantiate MCU command: {exc}")
            self._sync_buttons()
            return False

        mcu_command.play_sync_name.connect(self._play_mcu_callback, Qt.ConnectionType.QueuedConnection)
        mcu_command.start()

        self._mcu_command = mcu_command
        self._current_mcu_command_class = command_class
        self._active_mcu_context = context
        self._state = CommandExecutionState.RUNNING_MCU
        self._sync_buttons()
        return True

    def stop_mcu_command(self) -> None:
        if self._mcu_command is None:
            self._state = CommandExecutionState.RUNNING_PYTHON if self._command_runtime.is_running() else CommandExecutionState.IDLE
            self._sync_buttons()
            return

        try:
            self._mcu_command.end()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._logger.error(f"Failed to stop MCU command: {exc}")

        try:
            self._mcu_command.play_sync_name.disconnect(self._play_mcu_callback)
        except Exception:
            pass

        self._mcu_command = None
        self._active_mcu_context = None
        self._state = CommandExecutionState.RUNNING_PYTHON if self._command_runtime.is_running() else CommandExecutionState.IDLE
        self._sync_buttons()

    def stop_all(self, *, block: bool) -> None:
        self.stop_python_command(block=block)
        self.stop_mcu_command()

    def on_python_started(self, name: str) -> None:
        self._logger.info(f"Command started: {name}")

    def on_python_stopped(self, result: bool) -> None:
        _ = result
        self._pause_gamepad(False)
        self._set_frame_stream(False)
        self._active_python_context = None
        self._state = CommandExecutionState.RUNNING_MCU if self._mcu_command is not None else CommandExecutionState.IDLE
        self._sync_buttons()
