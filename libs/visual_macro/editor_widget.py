"""Qt widget for hosting the Visual Macro Blockly editor.

Final-form packaging direction
-----------------------------
- Visual Macro *documents* (JSON) are user-editable, so the default save/load
  directory is placed under the user's application data directory.
- Blockly editor assets (index.html / js / css / toolbox.json) are packaged as
  read-only resources and resolved in a way that works after `pip install`.
- Callers can still inject explicit `visual_macro_dir` / `ui_dir` if they want
  full control (e.g. tests, special builds, dev tools).
"""

from __future__ import annotations

import json
import os
from contextlib import ExitStack
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEventLoop, QUrl, Signal
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from libs.visual_macro.bridge import VisualMacroBridge
from libs.visual_macro.template_service import TemplateService

try:
    from platformdirs import user_data_path as _platform_user_data_path  # type: ignore
except Exception:  # pragma: no cover - fallback when dependency missing
    _platform_user_data_path = None

try:
    from importlib.resources import as_file, files as resource_files
except Exception:  # pragma: no cover
    as_file = None
    resource_files = None


APP_NAME = "SWCon-Pyside"


class VisualMacroEditorWidget(QWidget):
    """Host the Blockly-based Visual Macro editor in a Qt widget.

    Parameters
    ----------
    visual_macro_dir:
        Optional explicit directory used for user-editable Visual Macro JSON
        documents. If omitted, a per-user application data directory is used.
    ui_dir:
        Optional explicit directory that contains the editor web assets. If
        omitted, the packaged `ui.visual_macro` resources are used when
        available, with a development filesystem fallback.
    """

    run_requested = Signal(str)
    stop_requested = Signal()
    status_message = Signal(str)
    document_state_changed = Signal(str, bool)

    def __init__(
        self,
        visual_macro_dir: Optional[Path] = None,
        ui_dir: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        # Keep temporary extracted package-resource directories alive for the
        # lifetime of this widget.
        self._resource_stack: ExitStack = ExitStack()

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
        """Return the current document path relative to the Visual Macro base dir."""
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

    def save_current_document_interactive(self) -> Optional[bool]:
        """Save the current document, prompting for a path if needed.

        Returns
        -------
        True
            Saved successfully.
        False
            Save failed.
        None
            Save canceled by the user.
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
    def _default_visual_macro_dir(cls) -> Path:
        """Return the default save directory for user-editable Visual Macro JSON files."""
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

        target = root / "Commands" / "Visual"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _default_ui_dir(self) -> Path:
        """Return the directory containing the editor web assets.

        Preferred source:
        - packaged `ui.visual_macro` resources (works after pip install)

        Fallback source:
        - development tree `<repo>/ui/visual_macro`
        """
        # 1) packaged resource path
        if resource_files is not None and as_file is not None:
            try:
                traversable = resource_files("ui.visual_macro")
                # Keep the extracted dir alive for as long as the widget exists.
                real_path = self._resource_stack.enter_context(as_file(traversable))
                return Path(real_path)
            except Exception:
                pass

        # 2) development fallback (repo layout)
        dev_path = Path(__file__).resolve().parents[2] / "ui" / "visual_macro"
        if dev_path.exists():
            return dev_path

        # 3) cwd fallback for editable/dev oddities
        cwd_path = Path.cwd().resolve() / "ui" / "visual_macro"
        if cwd_path.exists():
            return cwd_path

        # Last resort: return the dev path even if missing so caller gets a clear file error.
        return dev_path

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming convention
        """Release any temporary extracted resource directories."""
        try:
            self._resource_stack.close()
        finally:
            super().closeEvent(event)
