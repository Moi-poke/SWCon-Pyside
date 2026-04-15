"""Repository helpers for stored Visual Macro documents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(slots=True, frozen=True)
class VisualMacroEntry:
    """Metadata for one stored Visual Macro document."""

    relative_path: str
    absolute_path: str
    display_name: str
    description: str
    tags: tuple[str, ...]


class VisualMacroRepository:
    """Access layer for Visual Macro files under Commands/Visual."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = (base_dir or Path("Commands/Visual")).resolve()

    @property
    def base_dir(self) -> Path:
        """Return the base directory for stored Visual Macro documents."""
        return self._base_dir

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a repository-relative path to an absolute path."""
        if not relative_path:
            raise ValueError("Visual Macro relative path must not be empty.")

        candidate = (self._base_dir / relative_path).resolve()
        if self._base_dir not in candidate.parents and candidate != self._base_dir:
            raise ValueError("Path traversal is not allowed.")

        return candidate

    def to_relative_path(self, path: str | Path) -> str:
        """Convert an absolute or repository-relative path into repository-relative form."""
        path_obj = Path(path)

        if not path_obj.is_absolute():
            normalized = path_obj.as_posix().lstrip("./")
            candidate = (self._base_dir / normalized).resolve()
        else:
            candidate = path_obj.resolve()

        if self._base_dir not in candidate.parents and candidate != self._base_dir:
            raise ValueError("The path must be inside Commands/Visual.")

        return candidate.relative_to(self._base_dir).as_posix()

    def load_document(self, relative_path: str) -> dict[str, Any]:
        """Load a Visual Macro document from disk.

        Supports:
        - current document format:
          {"format": "visual_macro_document", "version": "...", "metadata": ..., "workspace": ..., "program": ...}
        - legacy runtime-only format:
          {"version": "...", "root": ...}
        """
        file_path = self.resolve_path(relative_path)

        with file_path.open("r", encoding="utf-8") as f:
            raw_value = json.load(f)

        return self._normalize_document(raw_value)

    def save_document(self, relative_path: str, document: dict[str, Any]) -> Path:
        """Save a Visual Macro document to disk."""
        normalized = self._normalize_document(document)
        file_path = self.resolve_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        return file_path

    def list_entries(self) -> list[VisualMacroEntry]:
        """Return stored Visual Macro documents as metadata entries."""
        if not self._base_dir.exists():
            return []

        entries: list[VisualMacroEntry] = []

        for file_path in sorted(self._base_dir.glob("**/*.json")):
            try:
                relative_path = file_path.relative_to(self._base_dir).as_posix()
                document = self.load_document(relative_path)
                metadata = document.get("metadata", {})

                if not isinstance(metadata, dict):
                    metadata = {}

                display_name = str(metadata.get("name", "")).strip() or file_path.stem
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
                        absolute_path=file_path.as_posix(),
                        display_name=display_name,
                        description=description,
                        tags=tags,
                    )
                )
            except Exception:
                # 一覧取得では壊れたファイルをスキップする。
                continue

        return entries

    def delete_document(self, relative_path: str) -> None:
        """Delete a Visual Macro document from disk."""
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

        If new_relative_path is omitted, generate a copy name next to the original:
        - sample_macro.json -> sample_macro Copy.json
        - sample_macro Copy.json -> sample_macro Copy 2.json
        """
        source_relative_path = self.to_relative_path(source_relative_path)
        source_path = self.resolve_path(source_relative_path)

        if not source_path.exists():
            raise FileNotFoundError(source_path)

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
        """Return a non-conflicting repository-relative path."""
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
        """Generate a duplicate file name for a given source file."""
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
