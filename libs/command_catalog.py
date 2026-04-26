"""Catalog for Python / MCU / Visual command descriptors.

Clean final-form direction
--------------------------
This catalog is designed for a packaged desktop application where resources are
split into three layers:

1) user data directories (read-write, highest priority)
2) builtin packaged commands (read-only, optional)
3) development repo Commands/ fallback (read-only, lowest priority)

It works with the revised CommandLoader that supports multiple filesystem roots
and multiple package roots with stable precedence.
"""

from __future__ import annotations

import inspect
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional

from PySide6.QtGui import QColor

from libs.CommandBase import CommandBase
from libs.CommandLoader import CommandLoader, CommandSource
from libs.mcu_command_base import McuCommand

try:
    from platformdirs import user_data_path as _platform_user_data_path  # type: ignore
except Exception:  # pragma: no cover - fallback when dependency missing
    _platform_user_data_path = None

try:
    from importlib.resources import files as resource_files
except Exception:  # pragma: no cover
    resource_files = None


APP_NAME = "SWCon-Pyside"


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
    """Load commands and expose Python / MCU / Visual descriptors.

    Search precedence
    -----------------
    - User commands (user data dir) win over everything.
    - Builtin packaged commands come next.
    - Development repo Commands/ fallback is last.
    """

    BUILTIN_PYTHON_PACKAGE = "libs.builtin_commands.python"
    BUILTIN_MCU_PACKAGE = "libs.builtin_commands.mcu"
    BUILTIN_VISUAL_PACKAGE = "libs.builtin_commands.visual"

    def __init__(self) -> None:
        self._py_loader: Optional[CommandLoader] = None
        self._mcu_loader: Optional[CommandLoader] = None

        self._python_descriptors: list[CommandDescriptor] = []
        self._mcu_descriptors: list[CommandDescriptor] = []
        self._visual_descriptors: list[CommandDescriptor] = []

        self._python_errors: dict[str, Any] = {}
        self._mcu_errors: dict[str, Any] = {}
        self._visual_errors: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def python_descriptors(self) -> list[CommandDescriptor]:
        return list(self._python_descriptors)

    @property
    def mcu_descriptors(self) -> list[CommandDescriptor]:
        return list(self._mcu_descriptors)

    @property
    def visual_descriptors(self) -> list[CommandDescriptor]:
        return list(self._visual_descriptors)

    @property
    def python_errors(self) -> dict[str, Any]:
        return dict(self._python_errors)

    @property
    def mcu_errors(self) -> dict[str, Any]:
        return dict(self._mcu_errors)

    @property
    def visual_errors(self) -> dict[str, Any]:
        return dict(self._visual_errors)

    # ------------------------------------------------------------------
    # Load / reload
    # ------------------------------------------------------------------

    def load(self) -> None:
        self._py_loader = self._build_python_loader()
        self._mcu_loader = self._build_mcu_loader()

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

    # ------------------------------------------------------------------
    # Descriptor access helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Loader builders
    # ------------------------------------------------------------------

    def _build_python_loader(self) -> CommandLoader:
        user_root = self._user_commands_root("Python")
        dev_root = self._dev_commands_root("Python")
        filesystem_roots = [p for p in [user_root, dev_root] if p is not None]
        fs_kinds = ["user"] if user_root is not None else []
        if dev_root is not None:
            fs_kinds.append("dev")

        package_roots = [self.BUILTIN_PYTHON_PACKAGE]
        pkg_kinds = ["builtin"]

        return CommandLoader(
            base_class=CommandBase,
            filesystem_roots=filesystem_roots,
            package_roots=package_roots,
            fs_kinds=fs_kinds,
            pkg_kinds=pkg_kinds,
        )

    def _build_mcu_loader(self) -> CommandLoader:
        user_root = self._user_commands_root("MCU")
        dev_root = self._dev_commands_root("MCU")
        filesystem_roots = [p for p in [user_root, dev_root] if p is not None]
        fs_kinds = ["user"] if user_root is not None else []
        if dev_root is not None:
            fs_kinds.append("dev")

        package_roots = [self.BUILTIN_MCU_PACKAGE]
        pkg_kinds = ["builtin"]

        return CommandLoader(
            base_class=McuCommand,
            filesystem_roots=filesystem_roots,
            package_roots=package_roots,
            fs_kinds=fs_kinds,
            pkg_kinds=pkg_kinds,
        )

    # ------------------------------------------------------------------
    # Build descriptors
    # ------------------------------------------------------------------

    def _build_python_descriptors(
        self, items: list[list[Any]]
    ) -> list[CommandDescriptor]:
        descriptors: list[CommandDescriptor] = []
        for item in items:
            command_class = item[0]
            display_name = str(getattr(command_class, "NAME", command_class.__name__))
            source_path = self._infer_source_path(
                command_class, CommandKind.PYTHON, self._py_loader
            )
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
            source_path = self._infer_source_path(
                command_class, CommandKind.MCU, self._mcu_loader
            )
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

    # ------------------------------------------------------------------
    # Visual macro loading (user > builtin > dev)
    # ------------------------------------------------------------------

    def load_visual_macros(self) -> None:
        descriptors: list[CommandDescriptor] = []
        self._visual_errors = {}
        seen_ids: set[str] = set()

        # 1) user roots
        user_root = self._user_commands_root("Visual")
        if user_root is not None:
            descriptors.extend(
                self._load_visual_from_fs_root(
                    user_root, source_kind="user", seen_ids=seen_ids
                )
            )

        # 2) builtin package
        descriptors.extend(
            self._load_visual_from_package(
                self.BUILTIN_VISUAL_PACKAGE, source_kind="builtin", seen_ids=seen_ids
            )
        )

        # 3) dev fallback
        dev_root = self._dev_commands_root("Visual")
        if dev_root is not None:
            descriptors.extend(
                self._load_visual_from_fs_root(
                    dev_root, source_kind="dev", seen_ids=seen_ids
                )
            )

        self._visual_descriptors = descriptors

    def _load_visual_from_fs_root(
        self,
        root: Path,
        *,
        source_kind: str,
        seen_ids: set[str],
    ) -> list[CommandDescriptor]:
        descriptors: list[CommandDescriptor] = []
        if not root.exists():
            return descriptors

        for file_path in sorted(root.rglob("*.json")):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
                metadata = raw.get("metadata", {})
                name = metadata.get("name") or file_path.stem
                description = metadata.get("description", "")
                relative_path = file_path.relative_to(root).as_posix()
                command_id = f"visual:{relative_path}"
                if command_id in seen_ids:
                    continue
                seen_ids.add(command_id)

                # Visual Macro の source_path は実ファイルを開くための相対パスとして使われる。
                # そのため "dev:" / "user:" / "builtin:" のような接頭辞は付けない。
                source_path = relative_path

                descriptors.append(
                    CommandDescriptor(
                        command_id=command_id,
                        kind=CommandKind.VISUAL,
                        display_name=str(name),
                        command_class=None,
                        source_path=source_path,
                        tooltip=str(description) if description else None,
                        foreground=QColor(255, 127, 80),
                    )
                )
            except Exception as exc:
                self._visual_errors[file_path.as_posix()] = [
                    "visual json load failed",
                    str(exc),
                ]
        return descriptors

    def _load_visual_from_package(
        self,
        package_name: str,
        *,
        source_kind: str,
        seen_ids: set[str],
    ) -> list[CommandDescriptor]:
        descriptors: list[CommandDescriptor] = []
        if resource_files is None:
            return descriptors
        try:
            root = resource_files(package_name)
        except Exception:
            return descriptors

        for node in self._iter_resource_json(root):
            try:
                raw = json.loads(node.read_text(encoding="utf-8"))
                metadata = raw.get("metadata", {})
                name = metadata.get("name") or node.name.rsplit(".", 1)[0]
                description = metadata.get("description", "")
                relative_path = self._resource_relative_path(root, node)
                command_id = f"visual:{relative_path}"
                if command_id in seen_ids:
                    continue
                seen_ids.add(command_id)

                # Visual Macro の source_path は repository 側でそのままファイル解決に使うため、
                # 論理ラベルは含めず、純粋な相対パスだけを保持する。
                source_path = relative_path

                descriptors.append(
                    CommandDescriptor(
                        command_id=command_id,
                        kind=CommandKind.VISUAL,
                        display_name=str(name),
                        command_class=None,
                        source_path=source_path,
                        tooltip=str(description) if description else None,
                        foreground=QColor(255, 127, 80),
                    )
                )
            except Exception as exc:
                self._visual_errors[
                    f"{package_name}:{getattr(node, 'name', '<unknown>')}"
                ] = [
                    "visual package json load failed",
                    str(exc),
                ]
        return descriptors

    @staticmethod
    def _iter_resource_json(root) -> Iterable[Any]:
        for child in root.iterdir():
            if child.is_file() and child.name.endswith(".json"):
                yield child
            elif child.is_dir():
                yield from CommandCatalog._iter_resource_json(child)

    @staticmethod
    def _resource_relative_path(root, node) -> str:
        # Traversable does not guarantee pathlib.Path API; build a logical relative path.
        try:
            return str(node).replace(str(root), "").lstrip("/\\")
        except Exception:
            return getattr(node, "name", "<resource>.json")

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_user_data_dir(app_name: str) -> Path:
        if os.name == "nt":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            return Path(base) / app_name
        if os.name == "posix" and "darwin" in os.sys.platform.lower():
            return Path.home() / "Library" / "Application Support" / app_name
        base = os.environ.get("XDG_DATA_HOME")
        if base:
            return Path(base) / app_name
        return Path.home() / ".local" / "share" / app_name

    def _user_commands_root(self, kind_dir: str) -> Optional[Path]:
        try:
            if _platform_user_data_path is not None:
                try:
                    root = Path(
                        _platform_user_data_path(
                            APP_NAME, appauthor=False, ensure_exists=True
                        )
                    )
                except TypeError:
                    root = Path(_platform_user_data_path(APP_NAME))
            else:
                root = self._fallback_user_data_dir(APP_NAME)
            target = root / "Commands" / kind_dir
            target.mkdir(parents=True, exist_ok=True)
            return target
        except Exception:
            return None

    @staticmethod
    def _dev_commands_root(kind_dir: str) -> Optional[Path]:
        # command_catalog.py is expected under <root>/libs/command_catalog.py
        candidate = Path(__file__).resolve().parent.parent / "Commands" / kind_dir
        if candidate.exists():
            return candidate
        # Additional cwd-based fallback for editable/dev oddities
        cwd_candidate = Path.cwd().resolve() / "Commands" / kind_dir
        if cwd_candidate.exists():
            return cwd_candidate
        return None

    # ------------------------------------------------------------------
    # Descriptor metadata helpers
    # ------------------------------------------------------------------

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
    def _infer_source_path(
        command_class: type[Any],
        kind: CommandKind,
        loader: Optional[CommandLoader],
    ) -> str:
        # Prefer explicit loader source info when available.
        if loader is not None:
            src = loader.get_source_info(command_class)
            if src is not None:
                return f"{src.kind}:{src.location}"

        # Fallback to physical source file if introspection works.
        try:
            source_file = inspect.getsourcefile(command_class)
        except Exception:
            source_file = None
        if source_file:
            source_path = Path(source_file).resolve()
            return source_path.as_posix()

        base_dir = "Commands/Python" if kind == CommandKind.PYTHON else "Commands/MCU"
        return f"legacy:{base_dir}/{command_class.__name__}.py"


if __name__ == "__main__":
    catalog = CommandCatalog()
    catalog.load()
    print("python:", [d.display_name for d in catalog.python_descriptors])
    print("mcu:", [d.display_name for d in catalog.mcu_descriptors])
    print("visual:", [d.display_name for d in catalog.visual_descriptors])
