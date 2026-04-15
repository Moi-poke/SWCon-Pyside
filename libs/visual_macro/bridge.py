"""Qt bridge between the Blockly UI and the Python Visual Macro backend."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from libs.visual_macro.errors import VisualMacroValidationError
from libs.visual_macro.schema import parse_program_json
from libs.visual_macro.template_service import TemplateService


class VisualMacroBridge(QObject):
    """Bridge object exposed to the web UI through QWebChannel."""

    run_requested = Signal(str)
    stop_requested = Signal()
    ui_message = Signal(str)
    document_state_changed = Signal(str, bool)
    highlight_block_requested = Signal(str)
    clear_block_highlight_requested = Signal()

    def __init__(
        self,
        visual_macro_dir: Path,
        template_service: TemplateService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._visual_macro_dir: Path = visual_macro_dir
        self._template_service: TemplateService = template_service or TemplateService()
        self._visual_macro_dir.mkdir(parents=True, exist_ok=True)

    @Slot(result=str)
    def get_template_list_json(self) -> str:
        """Return the template file list as a JSON string."""
        entries: list[dict[str, str]] = [
            {"name": entry.name, "relative_path": entry.relative_path}
            for entry in self._template_service.list_templates()
        ]
        return json.dumps(entries, ensure_ascii=False)

    @Slot(result=str)
    def get_visual_macro_base_dir(self) -> str:
        """Return the base directory for visual macro documents."""
        return str(self._visual_macro_dir.resolve())

    @Slot(str, bool)
    def update_document_state(self, relative_path: str, modified: bool) -> None:
        """Update the current editor document state."""
        self.document_state_changed.emit(relative_path, modified)

    @Slot(str, result=str)
    def load_visual_macro_json(self, relative_path: str) -> str:
        """Load a previously saved Visual Macro JSON file."""
        try:
            file_path: Path = self._resolve_safe_path(relative_path)
            return file_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.ui_message.emit(f"Visual Macro load failed: {exc}")
            return ""
        except ValueError as exc:
            self.ui_message.emit(str(exc))
            return ""

    @Slot(str, str, result=bool)
    def save_visual_macro_json(self, relative_path: str, content: str) -> bool:
        """Save Visual Macro JSON text to disk."""
        try:
            file_path: Path = self._resolve_safe_path(relative_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return True
        except OSError as exc:
            self.ui_message.emit(f"Visual Macro save failed: {exc}")
            return False
        except ValueError as exc:
            self.ui_message.emit(str(exc))
            return False

    @Slot(str, result=bool)
    def validate_program_json(self, content: str) -> bool:
        """Validate runtime program JSON using the typed schema parser."""
        try:
            parse_program_json(content)
        except VisualMacroValidationError as exc:
            self.ui_message.emit(f"Program validation failed: {exc}")
            return False
        return True

    @Slot(str, result=bool)
    def validate_visual_macro_document_json(self, content: str) -> bool:
        """Validate a visual macro document JSON payload."""
        try:
            document: Mapping[str, object] = self._parse_document_json(content)
            program_value: object = document["program"]
            program_text: str = json.dumps(program_value, ensure_ascii=False)
            parse_program_json(program_text)
        except (ValueError, VisualMacroValidationError) as exc:
            self.ui_message.emit(f"Document validation failed: {exc}")
            return False
        return True

    @Slot(str, str, result=bool)
    def save_visual_macro_document_json(self, relative_path: str, content: str) -> bool:
        """Validate and save a Visual Macro document JSON text to disk."""
        if not self.validate_visual_macro_document_json(content):
            return False
        return self.save_visual_macro_json(relative_path, content)

    @Slot(str, result=str)
    def load_visual_macro_document_json(self, relative_path: str) -> str:
        """Load a Visual Macro document JSON text from disk."""
        return self.load_visual_macro_json(relative_path)

    @Slot(str)
    def request_run(self, program_json: str) -> None:
        """Validate and emit a run request for runtime program JSON."""
        if not self.validate_program_json(program_json):
            return
        self.run_requested.emit(program_json)

    @Slot()
    def request_stop(self) -> None:
        """Emit a stop request."""
        self.stop_requested.emit()

    def resolve_document_path(self, relative_path: str) -> Path:
        """Resolve a document path under the visual macro directory."""
        return self._resolve_safe_path(relative_path)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve a safe file path under the Visual Macro directory."""
        if not relative_path:
            raise ValueError("Path must not be empty.")

        candidate: Path = (self._visual_macro_dir / relative_path).resolve()
        base_dir: Path = self._visual_macro_dir.resolve()

        if base_dir not in candidate.parents and candidate != base_dir:
            raise ValueError("Path traversal is not allowed.")

        return candidate

    @staticmethod
    def _parse_document_json(content: str) -> Mapping[str, object]:
        """Parse and validate a visual macro document envelope."""
        try:
            raw_value: object = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

        if not isinstance(raw_value, Mapping):
            raise ValueError("Document root must be an object.")

        format_value: object = raw_value.get("format")
        if format_value != "visual_macro_document":
            raise ValueError("Document.format must be 'visual_macro_document'.")

        version_value: object = raw_value.get("version")
        if not isinstance(version_value, str):
            raise ValueError("Document.version must be a string.")

        if "workspace" not in raw_value:
            raise ValueError("Missing required field: document.workspace")

        if "program" not in raw_value:
            raise ValueError("Missing required field: document.program")

        program_value: object = raw_value["program"]
        if not isinstance(program_value, Mapping):
            raise ValueError("Document.program must be an object.")

        return raw_value

    @Slot(result=str)
    def choose_open_document_path(self) -> str:
        """Open a file dialog and return a relative path under the visual macro dir."""
        base_dir: Path = self._visual_macro_dir.resolve()
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "Visual Macro を開く",
            str(base_dir),
            "Visual Macro JSON (*.json);;All Files (*)",
        )
        if not selected_path:
            return ""

        try:
            return self._absolute_to_relative_path(Path(selected_path))
        except ValueError as exc:
            self.ui_message.emit(str(exc))
            return ""

    @Slot(str, result=str)
    def choose_save_document_path(self, suggested_relative_path: str) -> str:
        """Open a save dialog and return a relative path under the visual macro dir."""
        base_dir: Path = self._visual_macro_dir.resolve()

        if suggested_relative_path:
            initial_path = base_dir / suggested_relative_path
        else:
            initial_path = base_dir / "sample_macro.json"

        selected_path, _ = QFileDialog.getSaveFileName(
            None,
            "Visual Macro を保存",
            str(initial_path),
            "Visual Macro JSON (*.json);;All Files (*)",
        )
        if not selected_path:
            return ""

        path_obj = Path(selected_path)
        if path_obj.suffix == "":
            path_obj = path_obj.with_suffix(".json")

        try:
            return self._absolute_to_relative_path(path_obj)
        except ValueError as exc:
            self.ui_message.emit(str(exc))
            return ""

    def _absolute_to_relative_path(self, path: Path) -> str:
        """Convert an absolute path to a safe relative path under the visual macro dir."""
        candidate: Path = path.resolve()
        base_dir: Path = self._visual_macro_dir.resolve()

        if base_dir not in candidate.parents and candidate != base_dir:
            raise ValueError(
                "選択したファイルは Visual Macro ディレクトリ配下である必要があります。"
            )

        return candidate.relative_to(base_dir).as_posix()
