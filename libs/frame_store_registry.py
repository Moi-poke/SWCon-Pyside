"""FrameStoreRegistry - 全スロットの FrameStore を束ね、相互参照を可能にする."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from libs.frame_store import FrameStore


class FrameStoreRegistry:
    """スレッドセーフな FrameStore の辞書."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stores: dict[int, "FrameStore"] = {}

    def register(self, slot_id: int, store: "FrameStore") -> None:
        with self._lock:
            self._stores[slot_id] = store

    def unregister(self, slot_id: int) -> None:
        with self._lock:
            self._stores.pop(slot_id, None)

    def get_store(self, slot_id: int) -> Optional["FrameStore"]:
        with self._lock:
            return self._stores.get(slot_id)

    def get_raw_frame(self, slot_id: int) -> Optional[np.ndarray]:
        """他スロットのフレームをコピーして返す."""
        store = self.get_store(slot_id)
        if store is None:
            return None
        return store.latest_raw_copy()

    @property
    def slot_ids(self) -> list[int]:
        with self._lock:
            return list(self._stores.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._stores)
