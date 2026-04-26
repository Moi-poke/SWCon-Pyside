from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

try:
    from platformdirs import user_data_path as _platform_user_data_path  # type: ignore
except Exception:  # pragma: no cover
    _platform_user_data_path = None

try:
    from importlib.resources import files as resource_files
except Exception:  # pragma: no cover
    resource_files = None


APP_NAME = "SWCon-Pyside"
BUILTIN_TEMPLATE_PACKAGE = "libs.resources.templates"

IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".webp",
}


@dataclass(slots=True, frozen=True)
class TemplateSource:
    kind: str  # "user" | "builtin" | "dev"
    relative_path: str
    absolute_path: str


@dataclass(slots=True, frozen=True)
class TemplateEntry:
    relative_path: str
    absolute_path: str
    source_kind: str
    display_name: str


class TemplateRepository:
    """Resolve template images from user / builtin / dev locations.

    Search order:
      1. user templates
      2. builtin packaged templates
      3. development fallback templates
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        builtin_package: str = BUILTIN_TEMPLATE_PACKAGE,
        dev_base_dir: Optional[Path] = None,
    ) -> None:
        self._base_dir = (base_dir or self._default_user_templates_dir()).resolve()
        self._builtin_package = builtin_package
        self._dev_base_dir = (
            dev_base_dir or self._default_dev_templates_dir()
        ).resolve()

        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        """Writable user template directory."""
        return self._base_dir

    def to_relative_path(self, path: str | Path) -> str:
        """Normalize a path into repository-relative form."""
        path_obj = Path(path)

        if not path_obj.is_absolute():
            return self._normalize_relative_path(path_obj.as_posix().lstrip("./"))

        candidate = path_obj.resolve()

        if self._base_dir in candidate.parents or candidate == self._base_dir:
            return candidate.relative_to(self._base_dir).as_posix()

        if self._dev_base_dir in candidate.parents or candidate == self._dev_base_dir:
            return candidate.relative_to(self._dev_base_dir).as_posix()

        raise ValueError("The path must be inside the template roots.")

    def resolve_user_path(self, relative_path: str) -> Path:
        """Return the canonical writable path for a template."""
        rel = self._normalize_relative_path(relative_path)
        candidate = (self._base_dir / rel).resolve()
        if self._base_dir not in candidate.parents and candidate != self._base_dir:
            raise ValueError("Path traversal is not allowed.")
        return candidate

    def resolve_existing_source(self, relative_path: str) -> TemplateSource:
        """Resolve a template from user -> builtin -> dev."""
        rel = self.to_relative_path(relative_path)

        user_path = self.resolve_user_path(rel)
        if user_path.exists():
            return TemplateSource(
                kind="user",
                relative_path=rel,
                absolute_path=user_path.as_posix(),
            )

        builtin_node = self._resolve_builtin_resource(rel)
        if builtin_node is not None:
            return TemplateSource(
                kind="builtin",
                relative_path=rel,
                absolute_path=f"builtin:{rel}",
            )

        dev_path = self._resolve_dev_path(rel)
        if dev_path.exists():
            return TemplateSource(
                kind="dev",
                relative_path=rel,
                absolute_path=dev_path.as_posix(),
            )

        raise FileNotFoundError(rel)

    def exists(self, relative_path: str) -> bool:
        try:
            self.resolve_existing_source(relative_path)
            return True
        except Exception:
            return False

    def read_bytes(self, relative_path: str) -> bytes:
        """Read template bytes from user / builtin / dev."""
        source = self.resolve_existing_source(relative_path)

        if source.kind == "user":
            return Path(source.absolute_path).read_bytes()

        if source.kind == "dev":
            return Path(source.absolute_path).read_bytes()

        builtin_node = self._resolve_builtin_resource(source.relative_path)
        if builtin_node is None:
            raise FileNotFoundError(source.relative_path)

        return builtin_node.read_bytes()

    def read_image(
        self,
        relative_path: str,
        flags: int = cv2.IMREAD_COLOR,
    ) -> Optional[np.ndarray]:
        """Read template image as OpenCV ndarray."""
        raw = self.read_bytes(relative_path)
        arr = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(arr, flags)
        return image

    def list_entries(self) -> list[TemplateEntry]:
        """Return merged template list with precedence user > builtin > dev."""
        entries_by_rel: dict[str, TemplateEntry] = {}

        # 1) dev fallback (lowest priority)
        if self._dev_base_dir.exists():
            for file_path in sorted(self._dev_base_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                rel = file_path.relative_to(self._dev_base_dir).as_posix()
                entries_by_rel.setdefault(
                    rel,
                    TemplateEntry(
                        relative_path=rel,
                        absolute_path=file_path.as_posix(),
                        source_kind="dev",
                        display_name=file_path.stem,
                    ),
                )

        # 2) builtin
        for entry in self._list_builtin_entries():
            entries_by_rel[entry.relative_path] = entry

        # 3) user
        if self._base_dir.exists():
            for file_path in sorted(self._base_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                rel = file_path.relative_to(self._base_dir).as_posix()
                entries_by_rel[rel] = TemplateEntry(
                    relative_path=rel,
                    absolute_path=file_path.as_posix(),
                    source_kind="user",
                    display_name=file_path.stem,
                )

        return sorted(entries_by_rel.values(), key=lambda e: e.relative_path.lower())

    def _list_builtin_entries(self) -> list[TemplateEntry]:
        entries: list[TemplateEntry] = []
        root = self._builtin_root()
        if root is None:
            return entries

        for node in self._iter_builtin_files(root):
            try:
                rel = self._builtin_relative_path(root, node)
                suffix = Path(rel).suffix.lower()
                if suffix not in IMAGE_SUFFIXES:
                    continue
                entries.append(
                    TemplateEntry(
                        relative_path=rel,
                        absolute_path=f"builtin:{rel}",
                        source_kind="builtin",
                        display_name=Path(rel).stem,
                    )
                )
            except Exception:
                continue

        return entries

    def _resolve_dev_path(self, relative_path: str) -> Path:
        rel = self._normalize_relative_path(relative_path)
        candidate = (self._dev_base_dir / rel).resolve()
        if (
            self._dev_base_dir not in candidate.parents
            and candidate != self._dev_base_dir
        ):
            raise ValueError("Path traversal is not allowed.")
        return candidate

    def _builtin_root(self):
        if resource_files is None:
            return None
        try:
            return resource_files(self._builtin_package)
        except Exception:
            return None

    def _resolve_builtin_resource(self, relative_path: str):
        root = self._builtin_root()
        if root is None:
            return None

        node = root
        for part in Path(relative_path).parts:
            node = node.joinpath(part)

        try:
            if node.is_file():
                return node
        except Exception:
            return None

        return None

    @staticmethod
    def _iter_builtin_files(root):
        for child in root.iterdir():
            if child.is_file():
                yield child
            elif child.is_dir():
                yield from TemplateRepository._iter_builtin_files(child)

    @staticmethod
    def _builtin_relative_path(root, node) -> str:
        try:
            return str(node).replace(str(root), "").lstrip("/\\")
        except Exception:
            return getattr(node, "name", "<resource>")

    @staticmethod
    def _normalize_relative_path(path: str) -> str:
        if not path:
            raise ValueError("Template relative path must not be empty.")

        normalized = Path(path.replace("\\", "/"))

        if normalized.is_absolute():
            raise ValueError(f"Absolute path is not allowed: {path}")

        if ".." in normalized.parts:
            raise ValueError(f"Path traversal is not allowed: {path}")

        return normalized.as_posix()

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

    @classmethod
    def _default_user_templates_dir(cls) -> Path:
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
            root = cls._fallback_user_data_dir(APP_NAME)

        return (root / "Templates").resolve()

    @staticmethod
    def _default_dev_templates_dir() -> Path:
        # template_repository.py is expected under <root>/libs/template_repository.py
        candidate = Path(__file__).resolve().parents[1] / "template"
        if candidate.exists():
            return candidate.resolve()

        cwd_candidate = Path.cwd().resolve() / "template"
        if cwd_candidate.exists():
            return cwd_candidate.resolve()

        return candidate.resolve()
