from __future__ import annotations

import threading
from typing import Optional

import numpy as np
from PySide6.QtGui import QImage


class FrameStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()

        self._preview: Optional[QImage] = None
        self._preview_seq: int = 0

        self._raw: Optional[np.ndarray] = None
        self._raw_seq: int = 0

    # ------------------------------
    # preview(QImage) for UI
    # ------------------------------
    def set_preview(self, image: QImage) -> None:
        with self._lock:
            self._preview = image.copy()
            self._preview_seq += 1

    def get_preview_if_new(self, last_seq: int) -> tuple[Optional[QImage], int]:
        with self._lock:
            if self._preview is None or self._preview_seq == last_seq:
                return None, last_seq
            return self._preview, self._preview_seq

    # ------------------------------
    # raw(np.ndarray) for command
    # ------------------------------
    def set_raw(self, frame: np.ndarray) -> None:
        with self._lock:
            self._raw = frame.copy()
            self._raw_seq += 1

    def latest_raw_copy(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._raw is None:
                return None
            return self._raw.copy()
