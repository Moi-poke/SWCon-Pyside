"""Template listing service for Visual Macro UI and runtime support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

_TEMPLATE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
)


@dataclass(slots=True, frozen=True)
class TemplateEntry:
    """Metadata for a template image file."""

    name: str
    relative_path: str


class TemplateService:
    """Provide access to template image files under the project's template directory."""

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the service.

        Args:
            template_dir: Optional explicit template directory. If omitted, the
                project-root ``template`` directory is used.
        """
        self._template_dir: Path = template_dir or self._default_template_dir()

    @property
    def template_dir(self) -> Path:
        """Return the template directory path."""
        return self._template_dir

    def list_templates(self) -> list:
        """Return all template files under the template directory.

        Returns:
            A sorted list of template metadata entries.
        """
        if not self._template_dir.exists() or not self._template_dir.is_dir():
            return []

        entries: list[TemplateEntry] = []
        for file_path in sorted(self._template_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in _TEMPLATE_EXTENSIONS:
                continue

            relative_path: str = file_path.relative_to(self._template_dir).as_posix()
            entries.append(
                TemplateEntry(
                    name=file_path.name,
                    relative_path=relative_path,
                )
            )

        return entries

    @staticmethod
    def _default_template_dir() -> Path:
        """Resolve the default project template directory."""
        return Path(__file__).resolve().parents[2] / "template"
