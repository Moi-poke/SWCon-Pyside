"""Qt widget for hosting the Visual Macro Blockly editor."""

from __future__ import annotations

from pathlib import Path
import json

from PySide6.QtCore import QUrl, Signal, QEventLoop
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from libs.visual_macro.bridge import VisualMacroBridge
from libs.visual_macro.template_service import TemplateService


class VisualMacroEditorWidget(QWidget):
    """Host the Blockly-based Visual Macro editor in a Qt widget."""

    run_requested = Signal(str)
    stop_requested = Signal()
    status_message = Signal(str)
    document_state_changed = Signal(str, bool)

    def __init__(
        self,
        visual_macro_dir: Path | None = None,
        ui_dir: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._visual_macro_dir: Path = (
            visual_macro_dir or self._default_visual_macro_dir()
        )
        self._ui_dir: Path = ui_dir or self._default_ui_dir()
        self._current_document_relative_path: str = ""
        self._is_document_modified: bool = False

        self._bridge: VisualMacroBridge = VisualMacroBridge(
            visual_macro_dir=self._visual_macro_dir,
            template_service=TemplateService(),
            parent=self,
        )
        self._channel: QWebChannel = QWebChannel(self)
        self._view: QWebEngineView = QWebEngineView(self)

        self._setup_ui()
        self._setup_web_channel()
        self._setup_signals()
        self.reload_editor()

    @property
    def bridge(self) -> VisualMacroBridge:
        """Return the underlying bridge object."""
        return self._bridge

    @property
    def view(self) -> QWebEngineView:
        """Return the web view hosting the editor."""
        return self._view

    @property
    def current_document_relative_path(self) -> str:
        """Return the current document path relative to the visual macro base dir."""
        return self._current_document_relative_path

    @property
    def current_document_path(self) -> str:
        """Return the current document absolute path, or an empty string if unsaved."""
        if not self._current_document_relative_path:
            return ""
        try:
            return str(
                self._bridge.resolve_document_path(self._current_document_relative_path)
            )
        except ValueError:
            return ""

    @property
    def is_document_modified(self) -> bool:
        """Return whether the current document has unsaved changes."""
        return self._is_document_modified

    def reload_editor(self) -> None:
        """Load or reload the local editor HTML page into the web view."""
        index_path: Path = self._ui_dir / "index.html"
        self._view.load(QUrl.fromLocalFile(str(index_path.resolve())))

    def set_startup_document_path(self, path: str) -> None:
        """Set the document path to open when the editor finishes initializing."""
        self._bridge.set_startup_document_path(path)

    def _setup_ui(self) -> None:
        """Create the internal widget layout."""
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

    def _setup_web_channel(self) -> None:
        """Register the bridge object with the page web channel."""
        self._channel.registerObject("visualMacroBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

    def _setup_signals(self) -> None:
        """Forward bridge signals to the widget-level signals."""
        self._bridge.run_requested.connect(self.run_requested)
        self._bridge.stop_requested.connect(self.stop_requested)
        self._bridge.ui_message.connect(self.status_message)
        self._bridge.document_state_changed.connect(self._on_document_state_changed)

    def _run_javascript_blocking(self, script: str) -> object:
        """Run JavaScript and wait synchronously for the result."""
        loop = QEventLoop(self)
        result_holder: dict[str, object] = {"value": None}

        def _callback(value: object) -> None:
            result_holder["value"] = value
            loop.quit()

        self._view.page().runJavaScript(script, _callback)
        loop.exec()
        return result_holder["value"]

    def collect_document_json(self) -> str:
        """Return the current Visual Macro document JSON from the web editor."""
        result = self._run_javascript_blocking(
            "window.collectVisualMacroDocumentJson ? "
            "window.collectVisualMacroDocumentJson() : '';"
        )
        return result if isinstance(result, str) else ""

    def mark_document_saved(self, relative_path: str) -> bool:
        """Notify the web editor that the current document has been saved."""
        encoded_path = json.dumps(relative_path, ensure_ascii=False)
        script = (
            "window.markVisualMacroDocumentSaved ? "
            f"window.markVisualMacroDocumentSaved({encoded_path}) : false;"
        )
        result = self._run_javascript_blocking(script)
        return bool(result)

    def open_document_by_path(self, relative_path: str) -> bool:
        """Open a Visual Macro document in the web editor by relative path."""
        encoded_path = json.dumps(relative_path, ensure_ascii=False)
        script = (
            "window.openVisualMacroDocumentByPath ? "
            f"window.openVisualMacroDocumentByPath({encoded_path}) : false;"
        )
        result = self._run_javascript_blocking(script)
        return bool(result)

    def create_new_document(self) -> bool:
        """Create a new Visual Macro document in the web editor."""
        script = (
            "window.createNewVisualMacroDocument ? "
            "window.createNewVisualMacroDocument() : false;"
        )
        result = self._run_javascript_blocking(script)
        return bool(result)

    def save_current_document_interactive(self) -> bool | None:
        """Save the current document, prompting for a path if needed.

        Returns:
            True: saved successfully
            False: save failed
            None: save canceled by the user
        """
        document_json = self.collect_document_json()
        if not document_json:
            self.status_message.emit(
                "Visual Macro document JSON を取得できませんでした。"
            )
            return False

        relative_path = self.current_document_relative_path
        if not relative_path:
            relative_path = self._bridge.choose_save_document_path("sample_macro.json")
            if not relative_path:
                return None

        ok = self._bridge.save_visual_macro_document_json(relative_path, document_json)
        if not ok:
            return False

        self.mark_document_saved(relative_path)
        return True

    def _on_document_state_changed(self, relative_path: str, modified: bool) -> None:
        """Update cached document state from the web editor."""
        self._current_document_relative_path = relative_path
        self._is_document_modified = modified
        self.document_state_changed.emit(relative_path, modified)

    @staticmethod
    def _default_visual_macro_dir() -> Path:
        """Return the default save directory for Visual Macro JSON files."""
        return Path(__file__).resolve().parents[2] / "Commands" / "Visual"

    @staticmethod
    def _default_ui_dir() -> Path:
        """Return the default directory containing the editor web assets."""
        return Path(__file__).resolve().parents[2] / "ui" / "visual_macro"
