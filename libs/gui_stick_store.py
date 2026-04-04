from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PolarStickValue:
    angle: float
    radius: float


class GuiStickStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._left: Optional[PolarStickValue] = None
        self._right: Optional[PolarStickValue] = None

    def set_left(self, angle: float, radius: float) -> None:
        with self._lock:
            self._left = None if radius <= 0.0 else PolarStickValue(angle, radius)

    def set_right(self, angle: float, radius: float) -> None:
        with self._lock:
            self._right = None if radius <= 0.0 else PolarStickValue(angle, radius)

    def snapshot(self) -> tuple[Optional[PolarStickValue], Optional[PolarStickValue]]:
        with self._lock:
            return self._left, self._right

    def clear(self) -> None:
        with self._lock:
            self._left = None
            self._right = None
