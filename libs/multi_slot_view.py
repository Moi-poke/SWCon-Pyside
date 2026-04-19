"""MultiSlotView — 並列表示コンテナ + レイアウト切替."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from libs.session_slot import SessionSlot
from libs.slot_panel_widget import SlotPanelWidget

logger = logging.getLogger(__name__)

_LAYOUT_DISPLAY_NAMES: dict[str, str] = {
    "single":      "1×1 シングル",
    "grid_2x2":    "2×2 グリッド",
    "horizontal":  "横並び",
    "vertical":    "縦並び",
}

# ストレッチ計算で使う最大行列数
_MAX_GRID_DIM = 4


class MultiSlotView(QWidget):
    """全スロットの並列プレビュー + 操作パネルを表示する."""

    # ---- signals (MainWindow が受け取る) ----
    active_slot_changed = Signal(int)             # slot_id
    layout_mode_changed = Signal(str)             # layout_key
    slot_start_requested = Signal(int)            # slot_id
    slot_stop_requested = Signal(int)             # slot_id
    camera_change_requested = Signal(int, int)    # slot_id, camera_id
    com_port_change_requested = Signal(int, str)  # slot_id, port

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._panels: list[SlotPanelWidget] = []
        self._active_slot_id: int = 0
        self._current_layout: str = "single"

        # 自身が最大限スペースを取るようにする
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )

        self._build_ui()

    # ================================================================
    # UI構築
    # ================================================================

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        # ---- ツールバー行 (高さ固定、スペースを取らない) ----
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)

        lbl = QLabel("レイアウト:")
        lbl.setStyleSheet("font-size: 12px;")
        toolbar.addWidget(lbl)

        self._combo_layout = QComboBox()
        for key, display in _LAYOUT_DISPLAY_NAMES.items():
            self._combo_layout.addItem(display, userData=key)
        self._combo_layout.currentIndexChanged.connect(self._on_layout_combo_changed)
        toolbar.addWidget(self._combo_layout)

        toolbar.addStretch()
        root.addLayout(toolbar)

        # ---- パネル用グリッド (QWidget コンテナでラップ) ----
        # QGridLayout を QWidget に載せ、addWidget(stretch=1) で
        # 残りスペースを確実に埋める。
        self._grid_container = QWidget()
        self._grid_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(2, 2, 2, 2)
        self._grid.setSpacing(4)
        root.addWidget(self._grid_container, stretch=1)

        # ---- プレビュータイマー ----
        self._preview_timer = QTimer(self)
        self._preview_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._preview_timer.setInterval(16)  # ~60fps
        self._preview_timer.timeout.connect(self._tick_preview)

    # ================================================================
    # Public API
    # ================================================================

    def setup_panels(
        self,
        session_slots: list[SessionSlot],
        active_slot_id: int = 0,
    ) -> None:
        """SessionSlot のリストからパネルを構築する (enabled のみ)."""
        # 既存パネルをクリア
        for p in self._panels:
            self._grid.removeWidget(p)
            p.deleteLater()
        self._panels.clear()

        # enabled なスロットだけパネルを作成
        for slot in session_slots:
            if not slot.config.enabled:
                continue

            # ★ parent を _grid_container にすることで、
            #   グリッドコンテナのサイズに追従する
            panel = SlotPanelWidget(slot.slot_id, parent=self._grid_container)
            panel.bind_session_slot(slot)

            # シグナル中継
            panel.activated.connect(self._on_panel_activated)
            panel.start_requested.connect(self.slot_start_requested.emit)
            panel.stop_requested.connect(self.slot_stop_requested.emit)
            panel.camera_change_requested.connect(self.camera_change_requested.emit)
            panel.com_port_change_requested.connect(self.com_port_change_requested.emit)

            self._panels.append(panel)

        # アクティブスロットが enabled パネルに含まれるか確認
        if not self._find_panel(active_slot_id):
            active_slot_id = self._panels[0].slot_id if self._panels else 0

        self._active_slot_id = active_slot_id
        self._refresh_active_highlight()
        self._apply_layout()

    def panel(self, slot_id: int) -> Optional[SlotPanelWidget]:
        """slot_id に対応するパネルを返す."""
        return self._find_panel(slot_id)

    def set_layout_mode(self, mode: str) -> None:
        """プログラム的にレイアウトを変更する."""
        if mode not in _LAYOUT_DISPLAY_NAMES:
            mode = "single"
        self._current_layout = mode
        self._apply_layout()
        self.set_layout_combo_value(mode)

    def set_layout_combo_value(self, mode: str) -> None:
        """コンボボックスの選択を同期する (シグナル抑制)."""
        self._combo_layout.blockSignals(True)
        for i in range(self._combo_layout.count()):
            if self._combo_layout.itemData(i) == mode:
                self._combo_layout.setCurrentIndex(i)
                break
        self._combo_layout.blockSignals(False)

    def set_camera_list_all(self, camera_list: list[dict]) -> None:
        """全パネルにカメラ一覧をセットする."""
        for p in self._panels:
            p.set_camera_list(camera_list)

    def sync_slot_devices(self, session_slots: list[SessionSlot]) -> None:
        """スロット設定からカメラ/COMの表示を同期する."""
        for slot in session_slots:
            p = self._find_panel(slot.slot_id)
            if p is None:
                continue
            p.select_camera(slot.config.camera_id)
            p.set_com_port(slot.config.com_port)

    def start_preview(self) -> None:
        """プレビュータイマーを開始する."""
        if not self._preview_timer.isActive():
            self._preview_timer.start()

    def stop_preview(self) -> None:
        """プレビュータイマーを停止する."""
        self._preview_timer.stop()

    @property
    def active_slot_id(self) -> int:
        return self._active_slot_id

    @property
    def enabled_panel_count(self) -> int:
        return len(self._panels)

    # ================================================================
    # Internal — パネル検索
    # ================================================================

    def _find_panel(self, slot_id: int) -> Optional[SlotPanelWidget]:
        for p in self._panels:
            if p.slot_id == slot_id:
                return p
        return None

    # ================================================================
    # Internal — レイアウト
    # ================================================================

    def _apply_layout(self) -> None:
        """現在のレイアウト設定に従ってパネルを配置し直す."""
        # グリッドから全パネルを一旦外す
        for p in self._panels:
            self._grid.removeWidget(p)
            p.hide()

        # ストレッチをリセット
        for i in range(_MAX_GRID_DIM):
            self._grid.setRowStretch(i, 0)
            self._grid.setColumnStretch(i, 0)

        count = len(self._panels)
        if count == 0:
            return

        layout = self._current_layout
        used_rows = 0
        used_cols = 0

        if layout == "single":
            for p in self._panels:
                if p.slot_id == self._active_slot_id:
                    self._grid.addWidget(p, 0, 0)
                    p.show()
                    break
            used_rows = 1
            used_cols = 1

        elif layout == "horizontal":
            for i, p in enumerate(self._panels):
                self._grid.addWidget(p, 0, i)
                p.show()
            used_rows = 1
            used_cols = count

        elif layout == "vertical":
            for i, p in enumerate(self._panels):
                self._grid.addWidget(p, i, 0)
                p.show()
            used_rows = count
            used_cols = 1

        elif layout == "grid_2x2":
            cols = 2
            for i, p in enumerate(self._panels):
                r = i // cols
                c = i % cols
                self._grid.addWidget(p, r, c)
                p.show()
            used_rows = (count + cols - 1) // cols
            used_cols = min(count, cols)

        else:
            for i, p in enumerate(self._panels):
                self._grid.addWidget(p, i, 0)
                p.show()
            used_rows = count
            used_cols = 1

        # 使用行列にストレッチ係数を設定 → 均等に領域を分割
        for r in range(used_rows):
            self._grid.setRowStretch(r, 1)
        for c in range(used_cols):
            self._grid.setColumnStretch(c, 1)

    def _refresh_active_highlight(self) -> None:
        for p in self._panels:
            p.set_active(p.slot_id == self._active_slot_id)

    # ================================================================
    # Internal — slots
    # ================================================================

    @Slot(int)
    def _on_panel_activated(self, slot_id: int) -> None:
        if self._active_slot_id == slot_id:
            return
        self._active_slot_id = slot_id
        self._refresh_active_highlight()
        if self._current_layout == "single":
            self._apply_layout()
        self.active_slot_changed.emit(slot_id)

    @Slot(int)
    def _on_layout_combo_changed(self, index: int) -> None:
        key = self._combo_layout.itemData(index)
        if key and key != self._current_layout:
            self._current_layout = key
            self._apply_layout()
            self.layout_mode_changed.emit(key)

    @Slot()
    def _tick_preview(self) -> None:
        """全パネルのプレビューを更新する."""
        for p in self._panels:
            if p.isVisible():
                p.update_preview()
