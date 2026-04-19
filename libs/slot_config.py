"""SlotConfig - 1スロット分の設定データクラス."""
from __future__ import annotations

from dataclasses import dataclass

MAX_SLOTS = 4


@dataclass
class SlotConfig:
    """1スロットの設定."""

    slot_id: int = 0
    enabled: bool = False
    label: str = ""
    camera_id: int = -1
    camera_name: str = ""
    com_port: str = ""
    com_port_name: str = ""
    fps: int = 60

    def display_label(self) -> str:
        return self.label or f"Slot {self.slot_id}"

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "label": self.label,
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "com_port": self.com_port,
            "com_port_name": self.com_port_name,
            "fps": self.fps,
        }

    @classmethod
    def from_dict(cls, slot_id: int, data: dict) -> "SlotConfig":
        return cls(
            slot_id=slot_id,
            enabled=bool(data.get("enabled", False)),
            label=str(data.get("label", "")),
            camera_id=int(data.get("camera_id", -1)),
            camera_name=str(data.get("camera_name", "")),
            com_port=str(data.get("com_port", "")),
            com_port_name=str(data.get("com_port_name", "")),
            fps=int(data.get("fps", 60)),
        )

    @classmethod
    def defaults(cls) -> list["SlotConfig"]:
        """MAX_SLOTS 個のデフォルト設定リストを返す."""
        return [cls(slot_id=i) for i in range(MAX_SLOTS)]
