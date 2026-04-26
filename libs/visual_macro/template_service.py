"""Template listing service for Visual Macro UI and runtime support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from libs.template_repository import TemplateRepository


@dataclass(slots=True, frozen=True)
class TemplateEntry:
    """Metadata for a template image file shown in the UI."""

    name: str
    relative_path: str
    source_kind: str = ""


class TemplateService:
    """Provide access to template images through TemplateRepository.

    Design:
    - TemplateRepository owns the actual resolution policy:
        user -> builtin -> dev fallback
    - TemplateService is a thin adapter for UI / bridge use.
    """

    def __init__(
        self,
        template_dir: Path | None = None,
        repository: TemplateRepository | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            template_dir:
                Optional explicit writable user template directory.
                This is kept mainly for compatibility.
            repository:
                Optional explicit repository instance. If provided, it wins.
        """
        if repository is not None:
            self._repository = repository
        else:
            self._repository = TemplateRepository(base_dir=template_dir)

    @property
    def template_dir(self) -> Path:
        """Return the writable user template directory.

        This preserves the old property contract, but callers should prefer
        higher-level methods such as ``list_templates`` and ``read_bytes``.
        """
        return self._repository.base_dir

    @property
    def repository(self) -> TemplateRepository:
        """Expose the underlying repository."""
        return self._repository

    def list_templates(self) -> list[TemplateEntry]:
        """Return all visible template files.

        The list is already merged by repository precedence:
        user > builtin > dev fallback.
        """
        entries: list[TemplateEntry] = []
        for entry in self._repository.list_entries():
            entries.append(
                TemplateEntry(
                    name=entry.display_name or Path(entry.relative_path).name,
                    relative_path=entry.relative_path,
                    source_kind=entry.source_kind,
                )
            )
        return entries

    def exists(self, relative_path: str) -> bool:
        """Return whether a template exists in any source layer."""
        return self._repository.exists(relative_path)

    def read_bytes(self, relative_path: str) -> bytes:
        """Read template bytes from user / builtin / dev sources."""
        return self._repository.read_bytes(relative_path)

    def read_image(
        self,
        relative_path: str,
        flags: int = cv2.IMREAD_COLOR,
    ) -> Optional[np.ndarray]:
        """Read template image as OpenCV ndarray."""
        return self._repository.read_image(relative_path, flags=flags)

    def to_relative_path(self, path: str | Path) -> str:
        """Normalize a path into repository-relative form."""
        return self._repository.to_relative_path(path)
