"""Catalog for Python / MCU command descriptors (core version)."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Optional

from PySide6.QtGui import QColor

from libs.CommandBase import CommandBase
from libs.CommandLoader import CommandLoader
from libs.Utility import ospath
from libs.mcu_command_base import McuCommand


class CommandKind(str, Enum):
    """Kind of command handled by the application."""

    PYTHON = "python"
    MCU = "mcu"
    VISUAL = "visual"


@dataclass(slots=True, frozen=True)
class CommandDescriptor:
    """Metadata for a selectable command in the UI."""

    command_id: str
    kind: CommandKind
    display_name: str
    command_class: Optional[type[Any]]
    source_path: str
    tooltip: Optional[str] = None
    foreground: Optional[QColor] = None


class CommandCatalog:
    """Load commands and expose Python / MCU descriptors."""

    def __init__(self) -> None:
        self._py_loader: Optional[CommandLoader] = None
        self._mcu_loader: Optional[CommandLoader] = None

        self._python_descriptors: list[CommandDescriptor] = []
        self._mcu_descriptors: list[CommandDescriptor] = []
        self._visual_descriptors: list[CommandDescriptor] = []
        self._python_errors: dict[str, Any] = {}
        self._mcu_errors: dict[str, Any] = {}

    @property
    def python_descriptors(self) -> list[CommandDescriptor]:
        return list(self._python_descriptors)

    @property
    def mcu_descriptors(self) -> list[CommandDescriptor]:
        return list(self._mcu_descriptors)

    @property
    def visual_descriptors(self) -> list:
        return list(self._visual_descriptors)

    @property
    def python_errors(self) -> dict[str, Any]:
        return dict(self._python_errors)

    @property
    def mcu_errors(self) -> dict[str, Any]:
        return dict(self._mcu_errors)

    def load(self) -> None:
        self._py_loader = CommandLoader(ospath("Commands/Python"), CommandBase)
        self._mcu_loader = CommandLoader(ospath("Commands/MCU"), McuCommand)

        py_classes, py_errors = self._py_loader.load()
        mcu_classes, mcu_errors = self._mcu_loader.load()

        self._python_errors = py_errors
        self._mcu_errors = mcu_errors

        self._python_descriptors = self._build_python_descriptors(py_classes)
        self._mcu_descriptors = self._build_mcu_descriptors(mcu_classes)
        self.load_visual_macros()

    def reload(self) -> None:
        if self._py_loader is None or self._mcu_loader is None:
            self.load()
            return

        py_classes, py_errors = self._py_loader.reload()
        mcu_classes, mcu_errors = self._mcu_loader.reload()

        self._python_errors = py_errors
        self._mcu_errors = mcu_errors

        self._python_descriptors = self._build_python_descriptors(py_classes)
        self._mcu_descriptors = self._build_mcu_descriptors(mcu_classes)
        self.load_visual_macros()

    def get_python_descriptor(self, index: int) -> Optional[CommandDescriptor]:
        if index < 0 or index >= len(self._python_descriptors):
            return None
        return self._python_descriptors[index]

    def get_mcu_descriptor(self, index: int) -> Optional[CommandDescriptor]:
        if index < 0 or index >= len(self._mcu_descriptors):
            return None
        return self._mcu_descriptors[index]

    def get_visual_descriptor(self, index: int) -> Optional[CommandDescriptor]:
        if index < 0 or index >= len(self._visual_descriptors):
            return None
        return self._visual_descriptors[index]

    def find_python_index_by_name(self, name: str) -> int:
        for index, descriptor in enumerate(self._python_descriptors):
            if descriptor.display_name == name:
                return index
        return -1

    def find_mcu_index_by_name(self, name: str) -> int:
        for index, descriptor in enumerate(self._mcu_descriptors):
            if descriptor.display_name == name:
                return index
        return -1

    def find_visual_index_by_name(self, name: str) -> int:
        for index, descriptor in enumerate(self._visual_descriptors):
            if descriptor.display_name == name:
                return index
        return -1

    def _build_python_descriptors(
        self, items: list[list[Any]]
    ) -> list[CommandDescriptor]:
        descriptors: list[CommandDescriptor] = []
        for item in items:
            command_class = item[0]
            display_name = str(getattr(command_class, "NAME", command_class.__name__))
            source_path = self._infer_source_path(command_class, CommandKind.PYTHON)
            command_id = self._build_command_id(
                CommandKind.PYTHON.value, source_path, command_class.__name__
            )
            descriptors.append(
                CommandDescriptor(
                    command_id=command_id,
                    kind=CommandKind.PYTHON,
                    display_name=display_name,
                    command_class=command_class,
                    source_path=source_path,
                    tooltip=self._safe_get_tooltip(command_class),
                    foreground=QColor(255, 0, 0),
                )
            )
        return descriptors

    def _build_mcu_descriptors(self, items: list[list[Any]]) -> list[CommandDescriptor]:
        descriptors: list[CommandDescriptor] = []
        for item in items:
            command_class = item[0]
            display_name = str(getattr(command_class, "NAME", command_class.__name__))
            source_path = self._infer_source_path(command_class, CommandKind.MCU)
            command_id = self._build_command_id(
                CommandKind.MCU.value, source_path, command_class.__name__
            )
            descriptors.append(
                CommandDescriptor(
                    command_id=command_id,
                    kind=CommandKind.MCU,
                    display_name=display_name,
                    command_class=command_class,
                    source_path=source_path,
                    tooltip=None,
                    foreground=None,
                )
            )
        return descriptors

    @staticmethod
    def _build_command_id(prefix: str, source_path: str, class_name: str) -> str:
        return f"{prefix}:{source_path}:{class_name}"

    @staticmethod
    def _safe_get_tooltip(command_class: type[Any]) -> Optional[str]:
        try:
            instance = command_class()
        except Exception:
            return None
        value = getattr(instance, "__tool_tip__", None)
        return str(value) if value is not None else None

    @staticmethod
    def _infer_source_path(command_class: type[Any], kind: CommandKind) -> str:
        try:
            source_file = inspect.getsourcefile(command_class)
        except Exception:
            source_file = None

        if source_file:
            source_path = Path(source_file).resolve()
            try:
                return source_path.relative_to(Path.cwd().resolve()).as_posix()
            except Exception:
                return source_path.as_posix()

        base_dir = "Commands/Python" if kind == CommandKind.PYTHON else "Commands/MCU"
        return f"{base_dir}/{command_class.__name__}.py"

    def load_visual_macros(self) -> None:
        visual_dir = Path("Commands/Visual")
        descriptors: list[CommandDescriptor] = []

        if not visual_dir.exists():
            self._visual_descriptors = []
            return

        for file_path in sorted(visual_dir.glob("**/*.json")):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    raw = json.load(f)

                metadata = raw.get("metadata", {})
                name = metadata.get("name") or file_path.stem
                description = metadata.get("description", "")

                relative_path = file_path.relative_to(visual_dir).as_posix()
                command_id = f"visual:{relative_path}"

                descriptors.append(
                    CommandDescriptor(
                        command_id=command_id,
                        kind=CommandKind.VISUAL,
                        display_name=str(name),
                        command_class=None,
                        source_path=relative_path,
                        tooltip=str(description) if description else None,
                        foreground=QColor(255, 127, 80),
                    )
                )
            except Exception:
                # 必要なら後で visual_errors を足す
                pass

        self._visual_descriptors = descriptors
