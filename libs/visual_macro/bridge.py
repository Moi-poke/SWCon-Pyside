"""Qt bridge between the Blockly UI and the Python Visual Macro backend."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QBuffer, QIODevice, QObject, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QFileDialog

from libs.visual_macro.errors import VisualMacroValidationError
from libs.visual_macro.repository import VisualMacroRepository
from libs.visual_macro.schema import parse_program_json
from libs.visual_macro.template_service import TemplateService


class VisualMacroBridge(QObject):
    """Bridge object exposed to the web UI through QWebChannel.

    Design:
    - writable Visual Macro directory is represented by ``repository.base_dir``
      (typically the user data dir)
    - actual document loading is delegated to ``VisualMacroRepository`` so that
      user / builtin / dev fallback resolution stays consistent with the rest of
      the application
    """

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
        repository: VisualMacroRepository | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._template_service: TemplateService = template_service or TemplateService()
        self._startup_document_path: str = ""

        # Centralize document resolution / loading / saving policy here.
        self._repository: VisualMacroRepository = repository or VisualMacroRepository(
            base_dir=visual_macro_dir
        )

        # Keep a writable base-dir alias for compatibility / convenience.
        self._visual_macro_dir: Path = self._repository.base_dir
        self._visual_macro_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Template list
    # ------------------------------------------------------------------

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
        """Return the writable base directory for visual macro documents."""
        return str(self._repository.base_dir.resolve())

    # ------------------------------------------------------------------
    # Document state
    # ------------------------------------------------------------------

    @Slot(str, bool)
    def update_document_state(self, relative_path: str, modified: bool) -> None:
        """Update the current editor document state."""
        self.document_state_changed.emit(relative_path, modified)

    def set_startup_document_path(self, path: str) -> None:
        """Set the document path to open when the editor finishes initializing."""
        self._startup_document_path = path

    @Slot(result=str)
    def get_startup_document_path(self) -> str:
        """Return the startup document path (called once from JS on init)."""
        return self._startup_document_path

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    @Slot(str, result=str)
    def load_visual_macro_json(self, relative_path: str) -> str:
        """Load a previously saved Visual Macro JSON file.

        Uses VisualMacroRepository so that user / builtin / dev fallback are
        resolved consistently.
        """
        try:
            normalized_relative_path = self._repository.to_relative_path(relative_path)
            document = self._repository.load_document(normalized_relative_path)
            return json.dumps(document, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.ui_message.emit(f"Visual Macro load failed: {exc}")
            return ""
        except (ValueError, FileNotFoundError) as exc:
            self.ui_message.emit(str(exc))
            return ""

    @Slot(str, str, result=bool)
    def save_visual_macro_json(self, relative_path: str, content: str) -> bool:
        """Save Visual Macro JSON text to disk.

        Save target is always the writable repository base dir (user data dir).
        """
        try:
            normalized_relative_path = self._repository.to_relative_path(relative_path)

            raw_value = json.loads(content)
            if not isinstance(raw_value, Mapping):
                raise ValueError("Document root must be an object.")

            self._repository.save_document(
                normalized_relative_path,
                dict(raw_value),
            )
            return True
        except OSError as exc:
            self.ui_message.emit(f"Visual Macro save failed: {exc}")
            return False
        except (ValueError, json.JSONDecodeError) as exc:
            self.ui_message.emit(str(exc))
            return False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Run / Stop
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # File dialogs
    # ------------------------------------------------------------------

    def resolve_document_path(self, relative_path: str) -> Path:
        """Resolve a document path to the writable repository location.

        This intentionally returns the user-writable canonical path, even if the
        current document was originally loaded from builtin/dev fallback.
        """
        return self._repository.resolve_path(relative_path)

    @Slot(result=str)
    def choose_open_document_path(self) -> str:
        """Open a file dialog and return a relative path under the writable visual macro dir.

        Note:
            This dialog is intentionally scoped to the writable/user document dir.
            Builtin documents are typically opened via startup path / catalog flow,
            not via arbitrary filesystem browsing.
        """
        base_dir: Path = self._repository.base_dir.resolve()
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "Visual Macro を開く",
            str(base_dir),
            "Visual Macro JSON (*.json);;All Files (*)",
        )
        if not selected_path:
            return ""

        try:
            return self._repository.to_relative_path(Path(selected_path))
        except ValueError as exc:
            self.ui_message.emit(str(exc))
            return ""

    @Slot(str, result=str)
    def choose_save_document_path(self, suggested_relative_path: str) -> str:
        """Open a save dialog and return a relative path under the writable visual macro dir."""
        base_dir: Path = self._repository.base_dir.resolve()

        initial_relative_path = "sample_macro.json"
        if suggested_relative_path:
            try:
                initial_relative_path = self._repository.to_relative_path(
                    suggested_relative_path
                )
            except ValueError:
                initial_relative_path = "sample_macro.json"

        initial_path = base_dir / initial_relative_path

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
            return self._repository.to_relative_path(path_obj)
        except ValueError as exc:
            self.ui_message.emit(str(exc))
            return ""

    # ------------------------------------------------------------------
    # Capture frame (for ROI selection)
    # ------------------------------------------------------------------

    @Slot(result=str)
    def get_current_frame_base64(self) -> str:
        """Return the current capture frame as a base64-encoded PNG string.

        Parent chain: Bridge -> EditorWidget -> QDockWidget -> MainWindow
        MainWindow has ``frame_store: FrameStore``.

        Strategy:
          1. Try ``frame_store.latest_raw_copy()`` (np.ndarray, BGR).
             Available when frame_stream is enabled (script running).
          2. Fall back to ``frame_store.latest_preview_copy()`` (QImage).
             Available whenever the camera is connected (always updated).
        """
        try:
            frame_store = self._find_frame_store()
            if frame_store is None:
                return ""

            # --- Strategy 1: raw frame (available during script execution) ---
            raw_frame = frame_store.latest_raw_copy()
            if raw_frame is not None:
                import cv2

                _, buf = cv2.imencode(".png", raw_frame)
                return base64.b64encode(buf.tobytes()).decode("ascii")

            # --- Strategy 2: preview QImage (always available with camera) ---
            preview_image: QImage | None = frame_store.latest_preview_copy()
            if preview_image is not None and not preview_image.isNull():
                if preview_image.format() != QImage.Format.Format_ARGB32:
                    preview_image = preview_image.convertToFormat(
                        QImage.Format.Format_ARGB32
                    )
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                if preview_image.save(buffer, "PNG"):
                    raw_bytes: bytes = bytes(buffer.data())
                    return base64.b64encode(raw_bytes).decode("ascii")

            return ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Template preview
    # ------------------------------------------------------------------

    @Slot(str, result=str)
    def get_template_preview_base64(self, template_relative_path: str) -> str:
        """Return a template image as a base64-encoded string."""
        try:
            if not template_relative_path:
                return ""

            raw_bytes = self._template_service.read_bytes(template_relative_path)
            return base64.b64encode(raw_bytes).decode("ascii")
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_frame_store(self) -> object | None:
        """Walk the parent chain to find an object with a ``frame_store`` attr.

        Expected chain:
            Bridge (self)
            -> VisualMacroEditorWidget  (parent in __init__)
            -> QDockWidget              (dock.setWidget(editor))
            -> MainWindow               (has frame_store: FrameStore)
        """
        obj = self.parent()
        while obj is not None:
            if hasattr(obj, "frame_store"):
                return obj.frame_store  # type: ignore[return-value]
            obj = (
                obj.parent()
                if hasattr(obj, "parent") and callable(obj.parent)
                else None
            )
        return None

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
