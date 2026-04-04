from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal


class McuCommand(QObject):
    play_sync_name = Signal(str)

    __directory__ = "./Commands/MCU"

    def __init__(self, sync_name: str) -> None:
        super().__init__()
        self.isRunning = False
        self.sync_name = sync_name
        self.postProcess: Optional[Callable[[], None]] = None

    def start(self, postProcess: Optional[Callable[[], None]] = None) -> None:
        self.writeRow(self.sync_name)
        self.isRunning = True
        self.postProcess = postProcess

    def end(self) -> None:
        self.writeRow("end")
        self.isRunning = False
        if self.postProcess is not None:
            self.postProcess()

    def writeRow(self, s: str) -> None:
        self.play_sync_name.emit(s)
