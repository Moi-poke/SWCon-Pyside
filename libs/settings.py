import toml
from typing import Any
from libs.slot_config import MAX_SLOTS, SlotConfig

DEFAULT_SETTINGS = {
    "main_window": {
        "show_camera_realtime": False,
        "show_serial": False,
        "keyboard_control": False,
        "tab": "python",
        "must": {
            "fps": "60",
            "com_port": "",
            "com_port_name": "",
            "camera_id": "",
            "camera_name": "",
        },
        "option": {
            "window_size_width": 948,
            "window_size_height": 796,
            "window_showMaximized": False,
            "show_serial": True,
        },
    },
    "line": {"token_1": ""},
    "command": {
        "py_command": "A連打",
        "mcu_command": "A連打",
        "visual_macro_command": "",
    },
    "key_config": {
        "keyboard": {
            "button": {
                "Y": "K_y",
                "B": "K_b",
                "A": "K_a",
                "X": "K_x",
                "L": "K_l",
                "R": "K_r",
                "ZL": "K_k",
                "ZR": "K_e",
                "MINUS": "K_m",
                "PLUS": "K_p",
                "LCLICK": "K_q",
                "RCLICK": "K_w",
                "HOME": "K_h",
                "CAPTURE": "K_c",
            },
            "direction": {
                "UP": "K_UP",
                "RIGHT": "K_RIGHT",
                "DOWN": "K_DOWN",
                "LEFT": "K_LEFT",
                "UP_RIGHT": "",
                "DOWN_RIGHT": "",
                "DOWN_LEFT": "",
                "UP_LEFT": "",
            },
            "hat": {"TOP": "", "BTM": "", "LEFT": "", "RIGHT": ""},
        },
        "joystick": {
            "direction": {"LStick": True, "RStick": True},
            "button": {
                "Y": {"state": True, "assign": "button.3"},
                "B": {"state": True, "assign": "button.1"},
                "A": {"state": True, "assign": "button.0"},
                "X": {"state": True, "assign": "button.2"},
                "L": {"state": True, "assign": "button.9"},
                "R": {"state": True, "assign": "button.10"},
                "ZL": {"state": True, "assign": "axis.4"},
                "ZR": {"state": True, "assign": "axis.5"},
                "MINUS": {"state": True, "assign": "button.4"},
                "PLUS": {"state": True, "assign": "button.6"},
                "LCLICK": {"state": True, "assign": "button.7"},
                "RCLICK": {"state": True, "assign": "button.8"},
                "HOME": {"state": True, "assign": "button.5"},
                "CAPTURE": {"state": True, "assign": "button.15"},
            },
            "hat": {
                "TOP": {"state": True, "assign": "button.11"},
                "BTM": {"state": True, "assign": "button.12"},
                "LEFT": {"state": True, "assign": "button.13"},
                "RIGHT": {"state": True, "assign": "button.14"},
            },
        },
    },
    "slots": [
        {
            "enabled": True,
            "label": "Switch 1",
            "camera_id": 0,
            "camera_name": "",
            "com_port": "",
            "com_port_name": "",
            "fps": 60,
        },
        {
            "enabled": False,
            "label": "",
            "camera_id": -1,
            "camera_name": "",
            "com_port": "",
            "com_port_name": "",
            "fps": 60,
        },
        {
            "enabled": False,
            "label": "",
            "camera_id": -1,
            "camera_name": "",
            "com_port": "",
            "com_port_name": "",
            "fps": 60,
        },
        {
            "enabled": False,
            "label": "",
            "camera_id": -1,
            "camera_name": "",
            "com_port": "",
            "com_port_name": "",
            "fps": 60,
        },
    ],
    "multi_slot_layout": "grid_2x2",
    "active_gamepad_slot": 0,
}


class Setting:
    def __init__(self, path="./config/settings.toml") -> None:
        self.setting = None
        self.path = path

    @classmethod
    def alternate(cls, path: str):
        return cls(path=path)

    def load(self) -> bool:
        try:
            with open(self.path, encoding="utf-8") as setting:
                self.setting = toml.load(setting)
            self._migrate()
            return True
        except Exception:
            self.generate()
            self.save()
            self.load()
            return False

    def generate(self) -> bool:
        if self.setting is None:
            self.setting = DEFAULT_SETTINGS
            return True
        else:
            return False

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        """int() 変換に失敗したら default を返す."""
        try:
            rs = int(value)
            return rs
        except (ValueError, TypeError):
            return default

    def save(self) -> bool:
        if self.setting is not None:
            with open(self.path, "w", encoding="utf-8") as setting:
                toml.dump(self.setting, setting)
            return True
        else:
            return False

    # ================================================================
    # Multi-slot support
    # ================================================================

    def _migrate(self) -> None:
        """旧フォーマット (単一 camera/com_port) -> slots 配列へ変換."""
        if self.setting is None:
            return

        # ★ FIX A-3: command セクションにキーが不足していれば補完
        cmd = self.setting.setdefault("command", {})
        cmd.setdefault("py_command", "A連打")
        cmd.setdefault("mcu_command", "A連打")
        cmd.setdefault("visual_macro_command", "")

        if "slots" in self.setting:
            # 既に新フォーマット -> パディングだけ確認
            while len(self.setting["slots"]) < MAX_SLOTS:
                self.setting["slots"].append(
                    SlotConfig(slot_id=len(self.setting["slots"])).to_dict()
                )
            return

        # 旧設定から Slot 0 を生成
        must = self.setting.get("main_window", {}).get("must", {})
        slot0 = {
            "enabled": True,
            "label": "Switch 1",
            "camera_id": self._safe_int(must.get("camera_id", 0), 0),  # ★ FIX A-4
            "camera_name": str(must.get("camera_name", "")),
            "com_port": str(must.get("com_port", "")),
            "com_port_name": str(must.get("com_port_name", "")),
            "fps": self._safe_int(must.get("fps", 60), 60),  # ★ FIX A-4
        }
        slots = [slot0]
        for i in range(1, MAX_SLOTS):
            slots.append(SlotConfig(slot_id=i).to_dict())

        self.setting["slots"] = slots
        self.setting.setdefault("multi_slot_layout", "grid_2x2")
        self.setting.setdefault("active_gamepad_slot", 0)

    def get_slot_configs(self) -> list[SlotConfig]:
        """設定ファイルから SlotConfig のリストを返す."""
        raw_slots = self.setting.get("slots", [])
        configs: list[SlotConfig] = []
        for i, data in enumerate(raw_slots[:MAX_SLOTS]):
            configs.append(SlotConfig.from_dict(i, data))
        while len(configs) < MAX_SLOTS:
            configs.append(SlotConfig(slot_id=len(configs)))
        return configs

    def save_slot_configs(self, configs: list[SlotConfig]) -> None:
        """SlotConfig リストを設定ファイルに書き戻す."""
        self.setting["slots"] = [c.to_dict() for c in configs]
        self.save()


if __name__ == "__main__":
    s = Setting(path="../config/settings.toml")
    s.load()
    print(s.setting)
