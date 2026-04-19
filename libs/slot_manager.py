"""SlotManager - 全 SessionSlot のライフサイクルを管理する."""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Signal

from libs.frame_store_registry import FrameStoreRegistry
from libs.session_slot import SessionSlot
from libs.slot_config import MAX_SLOTS, SlotConfig

logger = logging.getLogger(__name__)


class SlotManager(QObject):
    """全 SessionSlot の作成・起動・停止を一元管理する."""

    slot_log = Signal(int, str, int)
    slot_command_started = Signal(int, str)
    slot_command_stopped = Signal(int, bool)
    slot_serial_state_changed = Signal(int, bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.frame_registry = FrameStoreRegistry()
        self._slots: list[SessionSlot] = []
        self._active_slot_index: int = 0

    @property
    def slots(self) -> list[SessionSlot]:
        return list(self._slots)

    @property
    def active_slot(self) -> Optional[SessionSlot]:
        if 0 <= self._active_slot_index < len(self._slots):
            return self._slots[self._active_slot_index]
        return None

    @property
    def active_slot_index(self) -> int:
        return self._active_slot_index

    def set_active_slot(self, index: int) -> None:
        if 0 <= index < len(self._slots):
            self._active_slot_index = index

    def slot(self, index: int) -> Optional[SessionSlot]:
        if 0 <= index < len(self._slots):
            return self._slots[index]
        return None

    @property
    def enabled_slots(self) -> list[SessionSlot]:
        return [s for s in self._slots if s.config.enabled]

    @property
    def enabled_count(self) -> int:
        return len(self.enabled_slots)

    def create_slots(self, configs: list[SlotConfig]) -> None:
        """設定リストからスロットを作成する."""
        for config in configs[:MAX_SLOTS]:
            slot = SessionSlot(
                config=config,
                frame_registry=self.frame_registry,
                parent=self,
            )
            slot.log_message.connect(self.slot_log.emit)
            slot.command_started.connect(self.slot_command_started.emit)
            slot.command_stopped.connect(self.slot_command_stopped.emit)
            slot.serial_state_changed.connect(
                self.slot_serial_state_changed.emit
            )
            self._slots.append(slot)
        logger.info("Created %d slot(s)", len(self._slots))

    def build_all_session_controllers(
        self, callback_factory: Callable[[SessionSlot], dict[str, Any]]
    ) -> None:
        """全スロットの CommandSessionController を構築する."""
        for slot in self._slots:
            kwargs = callback_factory(slot)
            slot.build_session_controller(**kwargs)

    def start_all(self) -> None:
        """有効な全スロットを起動する."""
        for slot in self._slots:
            if slot.config.enabled:
                slot.start()
                logger.info(
                    "Slot %d (%s) started",
                    slot.slot_id, slot.config.display_label(),
                )

    def shutdown_all(self, timeout_ms: int = 3000) -> None:
        """全スロットを安全にシャットダウンする."""
        for slot in self._slots:
            slot.shutdown(timeout_ms)
        self._slots.clear()
        logger.info("All slots shut down")

    def broadcast_start_python_command(
        self, command_class: type,
    ) -> list[bool]:
        """全有効スロットで同一コマンドを一斉開始する."""
        results: list[bool] = []
        for slot in self._slots:
            if not slot.config.enabled or slot.command_session is None:
                results.append(False)
                continue
            try:
                slot.command_session.start_python_command(command_class)
                results.append(True)
            except Exception as exc:
                logger.error(
                    "Slot %d: broadcast start failed: %s", slot.slot_id, exc,
                )
                results.append(False)
        return results

    def broadcast_stop_command(self) -> None:
        """全スロットのコマンドを停止する."""
        for slot in self._slots:
            if slot.command_session is not None:
                try:
                    slot.command_session.stop_all()
                except Exception as exc:
                    logger.error(
                        "Slot %d: broadcast stop failed: %s",
                        slot.slot_id, exc,
                    )

    def get_frame_from_slot(self, slot_id: int):
        """他スロットのフレームを取得 (ショートカット)."""
        return self.frame_registry.get_raw_frame(slot_id)
