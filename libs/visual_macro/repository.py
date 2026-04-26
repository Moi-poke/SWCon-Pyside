"""Repository helpers for stored Visual Macro documents."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from platformdirs import user_data_path as _platform_user_data_path  # type: ignore
except Exception:  # pragma: no cover
    _platform_user_data_path = None

try:
    from importlib.resources import files as resource_files
except Exception:  # pragma: no cover
    resource_files = None


APP_NAME = "SWCon-Pyside"
BUILTIN_VISUAL_PACKAGE = "libs.builtin_commands.visual"


@dataclass(slots=True, frozen=True)
class VisualMacroEntry:
    """Metadata for one stored Visual Macro document."""

    relative_path: str
    absolute_path: str
    display_name: str
    description: str
    tags: tuple[str, ...]


class VisualMacroRepository:
    """Access layer for Visual Macro files.

    Final-form design:
    - user documents (read/write): user data dir / Commands / Visual
    - builtin documents (read-only): package resources under libs.builtin_commands.visual
    - dev fallback (read-only): repo-root Commands / Visual

    Notes
    -----
    * `source_path` / `relative_path` is always a plain repository-relative path
      such as "sample_macro.json" or "folder/sub_macro.json".
    * Save / delete / duplicate targets are always written into the user data dir.
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        builtin_package: str = BUILTIN_VISUAL_PACKAGE,
        dev_base_dir: Optional[Path] = None,
    ) -> None:
        self._base_dir = (base_dir or self._default_user_visual_macro_dir()).resolve()
        self._builtin_package = builtin_package
        self._dev_base_dir = (
            dev_base_dir or self._default_dev_visual_macro_dir()
        ).resolve()

        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        """Return the writable base directory for stored user Visual Macro documents."""
        return self._base_dir

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a repository-relative path to an absolute *user-writable* path.

        This keeps the original method contract useful for save / delete / duplicate
        and for code paths that expect a writable canonical location.
        """
        relative_path = self.to_relative_path(relative_path)
        candidate = (self._base_dir / relative_path).resolve()
        if self._base_dir not in candidate.parents and candidate != self._base_dir:
            raise ValueError("Path traversal is not allowed.")
        return candidate

    def to_relative_path(self, path: str | Path) -> str:
        """Convert an absolute or repository-relative path into repository-relative form.

        Accepted:
        - relative path already rooted at Visual Macro repository semantics
        - absolute path under user visual dir
        - absolute path under dev visual dir

        Builtin package resources are represented as plain relative paths already,
        so they pass through unchanged.
        """
        path_obj = Path(path)

        if not path_obj.is_absolute():
            normalized = path_obj.as_posix().lstrip("./")
            candidate = (self._base_dir / normalized).resolve()
            if self._base_dir not in candidate.parents and candidate != self._base_dir:
                # Relative path outside user base_dir is still acceptable as long as
                # it is a plain relative repository path without traversal.
                return self._normalize_relative_path(normalized)
            return candidate.relative_to(self._base_dir).as_posix()

        candidate = path_obj.resolve()

        # user dir
        if self._base_dir in candidate.parents or candidate == self._base_dir:
            return candidate.relative_to(self._base_dir).as_posix()

        # dev fallback dir
        if self._dev_base_dir in candidate.parents or candidate == self._dev_base_dir:
            return candidate.relative_to(self._dev_base_dir).as_posix()

        raise ValueError("The path must be inside the Visual Macro roots.")

    def load_document(self, relative_path: str) -> dict[str, Any]:
        """Load a Visual Macro document.

        Search order:
        1. user data dir
        2. builtin package resources
        3. development fallback dir

        Supports:
        - current document format:
          {"format": "visual_macro_document", "version": "...", "metadata": ..., "workspace": ..., "program": ...}
        - legacy runtime-only format:
          {"version": "...", "root": ...}
        """
        relative_path = self.to_relative_path(relative_path)

        # 1) user
        user_path = self.resolve_path(relative_path)
        if user_path.exists():
            with user_path.open("r", encoding="utf-8") as f:
                raw_value = json.load(f)
            return self._normalize_document(raw_value)

        # 2) builtin
        builtin_node = self._resolve_builtin_resource(relative_path)
        if builtin_node is not None:
            raw_value = json.loads(builtin_node.read_text(encoding="utf-8"))
            return self._normalize_document(raw_value)

        # 3) dev fallback
        dev_path = self._resolve_dev_path(relative_path)
        if dev_path.exists():
            with dev_path.open("r", encoding="utf-8") as f:
                raw_value = json.load(f)
            return self._normalize_document(raw_value)

        raise FileNotFoundError(relative_path)

    def save_document(self, relative_path: str, document: dict[str, Any]) -> Path:
        """Save a Visual Macro document to the user data dir."""
        normalized = self._normalize_document(document)
        file_path = self.resolve_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        return file_path

    def list_entries(self) -> list[VisualMacroEntry]:
        """Return stored Visual Macro documents as metadata entries.

        Precedence:
        - user entries override builtin/dev entries with the same relative path
        - builtin entries override dev fallback entries with the same relative path
        """
        entries_by_relative_path: dict[str, VisualMacroEntry] = {}

        # 1) dev fallback (lowest priority)
        if self._dev_base_dir.exists():
            for file_path in sorted(self._dev_base_dir.glob("**/*.json")):
                entry = self._build_entry_from_fs_file(file_path, self._dev_base_dir)
                if entry is not None:
                    entries_by_relative_path.setdefault(entry.relative_path, entry)

        # 2) builtin package resources (middle priority)
        for entry in self._list_builtin_entries():
            entries_by_relative_path[entry.relative_path] = entry

        # 3) user dir (highest priority)
        if self._base_dir.exists():
            for file_path in sorted(self._base_dir.glob("**/*.json")):
                entry = self._build_entry_from_fs_file(file_path, self._base_dir)
                if entry is not None:
                    entries_by_relative_path[entry.relative_path] = entry

        return sorted(
            entries_by_relative_path.values(), key=lambda e: e.relative_path.lower()
        )

    def delete_document(self, relative_path: str) -> None:
        """Delete a user Visual Macro document from disk.

        Only user documents are writable/deletable. Builtin/dev documents are read-only.
        """
        file_path = self.resolve_path(relative_path)
        if not file_path.exists():
            raise FileNotFoundError(file_path)
        file_path.unlink()

    def duplicate_document(
        self,
        source_relative_path: str,
        new_relative_path: Optional[str] = None,
    ) -> str:
        """Duplicate a Visual Macro document and return the new relative path.

        The duplicated document is always written into the user data dir.

        If new_relative_path is omitted, generate a copy name next to the original:
        - sample_macro.json -> sample_macro Copy.json
        - sample_macro Copy.json -> sample_macro Copy 2.json
        """
        source_relative_path = self.to_relative_path(source_relative_path)
        document = self.load_document(source_relative_path)

        if new_relative_path is None:
            new_relative_path = self._generate_duplicate_relative_path(
                source_relative_path
            )
        else:
            new_relative_path = self.to_relative_path(new_relative_path)

        metadata = document.get("metadata", {})
        if isinstance(metadata, dict):
            current_name = str(metadata.get("name", "")).strip()
            if current_name:
                metadata["name"] = self._make_duplicate_display_name(current_name)
            document["metadata"] = metadata

        self.save_document(new_relative_path, document)
        return new_relative_path

    def ensure_unique_relative_path(self, requested_relative_path: str) -> str:
        """Return a non-conflicting repository-relative path in the user data dir."""
        requested_relative_path = self.to_relative_path(requested_relative_path)
        target = self.resolve_path(requested_relative_path)

        if not target.exists():
            return requested_relative_path

        stem = target.stem
        suffix = target.suffix
        parent = Path(requested_relative_path).parent

        counter = 2
        while True:
            candidate_name = f"{stem} {counter}{suffix}"
            candidate_relative = (
                (parent / candidate_name).as_posix()
                if str(parent) != "."
                else candidate_name
            )
            candidate_path = self.resolve_path(candidate_relative)
            if not candidate_path.exists():
                return candidate_relative
            counter += 1

    def _generate_duplicate_relative_path(self, source_relative_path: str) -> str:
        """Generate a duplicate file name for a given source file in the user data dir."""
        source_relative_path = self.to_relative_path(source_relative_path)
        source_path = Path(source_relative_path)

        parent = source_path.parent
        stem = source_path.stem
        suffix = source_path.suffix or ".json"

        copy_stem = f"{stem} Copy"
        candidate_relative = (
            (parent / f"{copy_stem}{suffix}").as_posix()
            if str(parent) != "."
            else f"{copy_stem}{suffix}"
        )

        candidate_path = self.resolve_path(candidate_relative)
        if not candidate_path.exists():
            return candidate_relative

        counter = 2
        while True:
            candidate_relative = (
                (parent / f"{copy_stem} {counter}{suffix}").as_posix()
                if str(parent) != "."
                else f"{copy_stem} {counter}{suffix}"
            )
            candidate_path = self.resolve_path(candidate_relative)
            if not candidate_path.exists():
                return candidate_relative
            counter += 1

    @staticmethod
    def _make_duplicate_display_name(name: str) -> str:
        """Generate a duplicated display name."""
        if not name:
            return "Copy"
        if name.endswith(" Copy"):
            return f"{name} 2"
        return f"{name} Copy"

    def _build_entry_from_fs_file(
        self,
        file_path: Path,
        root: Path,
    ) -> Optional[VisualMacroEntry]:
        """Build VisualMacroEntry from a filesystem JSON file."""
        try:
            relative_path = file_path.relative_to(root).as_posix()
            document = self.load_document(relative_path)
            metadata = document.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            display_name = str(metadata.get("name", "")).strip() or file_path.stem
            description = str(metadata.get("description", "")).strip()

            tags_value = metadata.get("tags", [])
            if isinstance(tags_value, list):
                tags = tuple(str(tag).strip() for tag in tags_value if str(tag).strip())
            else:
                tags = ()

            return VisualMacroEntry(
                relative_path=relative_path,
                absolute_path=file_path.as_posix(),
                display_name=display_name,
                description=description,
                tags=tags,
            )
        except Exception:
            # 一覧取得では壊れたファイルをスキップする。
            return None

    def _list_builtin_entries(self) -> list[VisualMacroEntry]:
        """List builtin Visual Macro documents from package resources."""
        entries: list[VisualMacroEntry] = []
        root = self._builtin_root()
        if root is None:
            return entries

        for node in self._iter_builtin_json(root):
            try:
                relative_path = self._builtin_relative_path(root, node)
                document = self.load_document(relative_path)
                metadata = document.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}

                display_name = (
                    str(metadata.get("name", "")).strip() or Path(relative_path).stem
                )
                description = str(metadata.get("description", "")).strip()

                tags_value = metadata.get("tags", [])
                if isinstance(tags_value, list):
                    tags = tuple(
                        str(tag).strip() for tag in tags_value if str(tag).strip()
                    )
                else:
                    tags = ()

                entries.append(
                    VisualMacroEntry(
                        relative_path=relative_path,
                        absolute_path=f"builtin:{relative_path}",
                        display_name=display_name,
                        description=description,
                        tags=tags,
                    )
                )
            except Exception:
                continue

        return entries

    def _resolve_dev_path(self, relative_path: str) -> Path:
        """Resolve a relative path inside the development fallback dir."""
        relative_path = self._normalize_relative_path(relative_path)
        candidate = (self._dev_base_dir / relative_path).resolve()
        if (
            self._dev_base_dir not in candidate.parents
            and candidate != self._dev_base_dir
        ):
            raise ValueError("Path traversal is not allowed.")
        return candidate

    def _builtin_root(self):
        """Return Traversable root for builtin visual macros, or None."""
        if resource_files is None:
            return None
        try:
            return resource_files(self._builtin_package)
        except Exception:
            return None

    def _resolve_builtin_resource(self, relative_path: str):
        """Return Traversable node for a builtin resource, or None."""
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
    def _iter_builtin_json(root):
        """Recursively iterate over builtin JSON Traversable nodes."""
        for child in root.iterdir():
            if child.is_file() and child.name.endswith(".json"):
                yield child
            elif child.is_dir():
                yield from VisualMacroRepository._iter_builtin_json(child)

    @staticmethod
    def _builtin_relative_path(root, node) -> str:
        """Compute a relative path string for a Traversable builtin JSON node."""
        try:
            return str(node).replace(str(root), "").lstrip("/\\")
        except Exception:
            return getattr(node, "name", "<resource>.json")

    @staticmethod
    def _normalize_relative_path(path: str) -> str:
        """Normalize relative path and reject dangerous traversal."""
        if not path:
            raise ValueError("Visual Macro relative path must not be empty.")

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
    def _default_user_visual_macro_dir(cls) -> Path:
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

        return (root / "Commands" / "Visual").resolve()

    @staticmethod
    def _default_dev_visual_macro_dir() -> Path:
        # repository.py is expected under <root>/libs/visual_macro/repository.py
        candidate = Path(__file__).resolve().parents[2] / "Commands" / "Visual"
        if candidate.exists():
            return candidate.resolve()

        cwd_candidate = Path.cwd().resolve() / "Commands" / "Visual"
        if cwd_candidate.exists():
            return cwd_candidate.resolve()

        return candidate.resolve()

    @staticmethod
    def _normalize_document(raw_value: Any) -> dict[str, Any]:
        """Normalize current and legacy formats into the current document envelope."""
        if not isinstance(raw_value, dict):
            raise ValueError("Visual Macro document root must be an object.")

        if raw_value.get("format") == "visual_macro_document":
            if "program" not in raw_value:
                raise ValueError("Visual Macro document is missing 'program'.")
            if "workspace" not in raw_value:
                raise ValueError("Visual Macro document is missing 'workspace'.")

            metadata = raw_value.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            normalized = dict(raw_value)
            normalized.setdefault("version", "1.0")
            normalized["metadata"] = {
                "name": str(metadata.get("name", "")).strip(),
                "description": str(metadata.get("description", "")).strip(),
                "tags": [
                    str(tag).strip()
                    for tag in metadata.get("tags", [])
                    if str(tag).strip()
                ]
                if isinstance(metadata.get("tags", []), list)
                else [],
            }
            return normalized

        if "version" in raw_value and "root" in raw_value:
            return {
                "format": "visual_macro_document",
                "version": "1.0",
                "metadata": {
                    "name": "",
                    "description": "",
                    "tags": [],
                },
                "workspace": {},
                "program": raw_value,
            }

        raise ValueError("Unsupported Visual Macro document format.")
