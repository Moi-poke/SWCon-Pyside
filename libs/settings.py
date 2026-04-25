from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Optional

import toml

from libs.slot_config import MAX_SLOTS, SlotConfig

try:
    # Recommended for per-user config locations across OSes.
    from platformdirs import user_config_path as _platform_user_config_path  # type: ignore
except Exception:  # pragma: no cover - fallback if dependency is unavailable
    _platform_user_config_path = None


APP_NAME = "SWCon-Pyside"
DEFAULT_SETTINGS_FILENAME = "settings.toml"

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


def _deepcopy_default_settings() -> dict:
    return copy.deepcopy(DEFAULT_SETTINGS)


def _fallback_user_config_dir(app_name: str) -> Path:
    """Fallback when platformdirs is unavailable.

    Windows: %APPDATA%/<app_name>
    macOS  : ~/Library/Application Support/<app_name>
    Linux  : $XDG_CONFIG_HOME/<app_name> or ~/.config/<app_name>
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / app_name
        return Path.home() / "AppData" / "Roaming" / app_name

    if os.name == "posix" and "darwin" in os.sys.platform.lower():
        return Path.home() / "Library" / "Application Support" / app_name

    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / app_name
    return Path.home() / ".config" / app_name


def _default_settings_path() -> Path:
    if _platform_user_config_path is not None:
        try:
            return (
                Path(
                    _platform_user_config_path(
                        APP_NAME, appauthor=False, ensure_exists=True
                    )
                )
                / DEFAULT_SETTINGS_FILENAME
            )
        except TypeError:
            # Older/newer platformdirs signatures may differ; fall back safely.
            return (
                Path(_platform_user_config_path(APP_NAME)) / DEFAULT_SETTINGS_FILENAME
            )
    return _fallback_user_config_dir(APP_NAME) / DEFAULT_SETTINGS_FILENAME


class Setting:
    def __init__(self, path: Optional[str] = None) -> None:
        self.setting: Optional[dict] = None
        self.path: Path = Path(path) if path else _default_settings_path()

    @classmethod
    def alternate(cls, path: str) -> "Setting":
        return cls(path=path)

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        """int() 変換に失敗したら default を返す."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _ensure_parent_dir(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _ensure_loaded_default(self) -> None:
        if self.setting is None:
            self.setting = _deepcopy_default_settings()

    def generate(self) -> bool:
        if self.setting is None:
            self.setting = _deepcopy_default_settings()
            self._migrate()
            return True
        return False

    def load(self) -> bool:
        """Load settings from the resolved path.

        Behavior:
        - If the file exists and is valid TOML, load + migrate.
        - If the file does not exist, create parent dirs, generate defaults, save,
          then return False (same semantic as legacy implementation).
        - If the file exists but is unreadable/invalid, fall back to defaults and save.
        """
        try:
            with self.path.open(encoding="utf-8") as setting_file:
                self.setting = toml.load(setting_file)
            self._migrate()
            return True
        except FileNotFoundError:
            self.generate()
            self.save()
            return False
        except Exception:
            # Corrupt/invalid TOML etc. -> regenerate clean defaults
            self.generate()
            self.save()
            return False

    def save(self) -> bool:
        self._ensure_loaded_default()
        self._migrate()
        self._ensure_parent_dir()
        with self.path.open("w", encoding="utf-8") as setting_file:
            toml.dump(self.setting, setting_file)
        return True

    # ================================================================
    # Multi-slot support
    # ================================================================
    def _migrate(self) -> None:
        """旧フォーマット (単一 camera/com_port) -> slots 配列へ変換・不足キー補完."""
        if self.setting is None:
            return

        # ルート不足キー
        self.setting.setdefault("multi_slot_layout", "grid_2x2")
        self.setting.setdefault("active_gamepad_slot", 0)

        # main_window 補完
        mw = self.setting.setdefault("main_window", {})
        mw.setdefault("show_camera_realtime", False)
        mw.setdefault("show_serial", False)
        mw.setdefault("keyboard_control", False)
        mw.setdefault("tab", "python")
        must = mw.setdefault("must", {})
        must.setdefault("fps", "60")
        must.setdefault("com_port", "")
        must.setdefault("com_port_name", "")
        must.setdefault("camera_id", "")
        must.setdefault("camera_name", "")
        option = mw.setdefault("option", {})
        option.setdefault("window_size_width", 948)
        option.setdefault("window_size_height", 796)
        option.setdefault("window_showMaximized", False)
        option.setdefault("show_serial", True)

        # command 補完
        cmd = self.setting.setdefault("command", {})
        cmd.setdefault("py_command", "A連打")
        cmd.setdefault("mcu_command", "A連打")
        cmd.setdefault("visual_macro_command", "")

        # line 補完
        line = self.setting.setdefault("line", {})
        line.setdefault("token_1", "")

        # key_config 補完（足りない場合は DEFAULT_SETTINGS から補う）
        if "key_config" not in self.setting:
            self.setting["key_config"] = copy.deepcopy(DEFAULT_SETTINGS["key_config"])
        else:
            self._merge_defaults(
                self.setting["key_config"], DEFAULT_SETTINGS["key_config"]
            )

        if "slots" in self.setting:
            # 既に新フォーマット -> パディング + 各slot補完
            while len(self.setting["slots"]) < MAX_SLOTS:
                self.setting["slots"].append(
                    SlotConfig(slot_id=len(self.setting["slots"])).to_dict()
                )
            if len(self.setting["slots"]) > MAX_SLOTS:
                self.setting["slots"] = self.setting["slots"][:MAX_SLOTS]
            for i, slot in enumerate(self.setting["slots"]):
                self._merge_defaults(slot, SlotConfig(slot_id=i).to_dict())
            return

        # 旧設定から Slot 0 を生成
        slot0 = {
            "enabled": True,
            "label": "Switch 1",
            "camera_id": self._safe_int(must.get("camera_id", 0), 0),
            "camera_name": str(must.get("camera_name", "")),
            "com_port": str(must.get("com_port", "")),
            "com_port_name": str(must.get("com_port_name", "")),
            "fps": self._safe_int(must.get("fps", 60), 60),
        }
        slots = [slot0]
        for i in range(1, MAX_SLOTS):
            slots.append(SlotConfig(slot_id=i).to_dict())

        self.setting["slots"] = slots

    @staticmethod
    def _merge_defaults(target: dict, defaults: dict) -> None:
        """Recursively fill missing keys in target using defaults."""
        for key, value in defaults.items():
            if key not in target:
                target[key] = copy.deepcopy(value)
            elif isinstance(target[key], dict) and isinstance(value, dict):
                Setting._merge_defaults(target[key], value)

    def get_slot_configs(self) -> list[SlotConfig]:
        """設定ファイルから SlotConfig のリストを返す."""
        self._ensure_loaded_default()
        self._migrate()
        raw_slots = self.setting.get("slots", [])
        configs: list[SlotConfig] = []
        for i, data in enumerate(raw_slots[:MAX_SLOTS]):
            configs.append(SlotConfig.from_dict(i, data))
        while len(configs) < MAX_SLOTS:
            configs.append(SlotConfig(slot_id=len(configs)))
        return configs

    def save_slot_configs(self, configs: list[SlotConfig]) -> None:
        """SlotConfig リストを設定ファイルに書き戻す."""
        self._ensure_loaded_default()
        self.setting["slots"] = [c.to_dict() for c in configs]
        self.save()


if __name__ == "__main__":
    s = Setting(path="../config/settings.toml")
    s.load()
    print(s.path)
    print(s.setting)
