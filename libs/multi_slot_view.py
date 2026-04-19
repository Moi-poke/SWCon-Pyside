"""MultiSlotView — 並列表示コンテナ + レイアウト切替."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
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
    "single": "1×1 シングル",
    "grid_2x2": "2×2 グリッド",
    "horizontal": "横並び",
    "vertical": "縦並び",
}

# ストレッチ計算で使う最大行列数
_MAX_GRID_DIM = 4


class MultiSlotView(QWidget):
    """全スロットの並列プレビュー + 操作パネルを表示する."""

    # ---- signals (MainWindow が受け取る) ----
    active_slot_changed = Signal(int)  # slot_id
    layout_mode_changed = Signal(str)  # layout_key
    slot_start_requested = Signal(int)  # slot_id
    slot_stop_requested = Signal(int)  # slot_id
    camera_change_requested = Signal(int, int)  # slot_id, camera_id
    com_port_change_requested = Signal(int, str)  # slot_id, port
    slot_enabled_changed = Signal(int, bool)  # slot_id, enabled  ★NEW

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._panels: list[SlotPanelWidget] = []
        self._slot_checkboxes: list[QCheckBox] = []
        self._active_slot_id: int = 0
        self._current_layout: str = "single"

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._build_ui()

    # ================================================================
    # UI構築
    # ================================================================

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        # ---- ツールバー行 ----
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

        # ---- スロット有効化チェックボックス用スペーサー + コンテナ ----
        toolbar.addSpacing(16)
        self._slot_cb_layout = QHBoxLayout()
        self._slot_cb_layout.setSpacing(8)
        toolbar.addLayout(self._slot_cb_layout)

        toolbar.addStretch()
        root.addLayout(toolbar)

        # ---- パネル用グリッド ----
        self._grid_container = QWidget()
        self._grid_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
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
        """SessionSlot のリストからパネルとチェックボックスを構築する (全スロット)."""
        # ---- 既存パネルをクリア ----
        for p in self._panels:
            self._grid.removeWidget(p)
            p.deleteLater()
        self._panels.clear()

        # ---- 既存チェックボックスをクリア ----
        while self._slot_cb_layout.count():
            item = self._slot_cb_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._slot_checkboxes.clear()

        # ---- 全スロットのパネル + チェックボックスを作成 ----
        for slot in session_slots:
            # -- パネル --
            panel = SlotPanelWidget(slot.slot_id, parent=self._grid_container)
            panel.bind_session_slot(slot)

            # シグナル中継
            panel.activated.connect(self._on_panel_activated)
            panel.start_requested.connect(self.slot_start_requested.emit)
            panel.stop_requested.connect(self.slot_stop_requested.emit)
            panel.camera_change_requested.connect(self.camera_change_requested.emit)
            panel.com_port_change_requested.connect(self.com_port_change_requested.emit)

            self._panels.append(panel)

            # -- チェックボックス --
            cb = QCheckBox(slot.config.display_label())
            cb.setChecked(slot.config.enabled)
            cb.setStyleSheet("font-size: 12px;")
            sid = slot.slot_id  # ループ変数キャプチャ対策
            cb.toggled.connect(
                lambda checked, s=sid: self._on_slot_checkbox_toggled(s, checked)
            )
            self._slot_cb_layout.addWidget(cb)
            self._slot_checkboxes.append(cb)

        # ---- アクティブスロット ----
        # active_slot_id が enabled パネルに含まれるか確認
        enabled_panels = self._enabled_panels()
        if enabled_panels:
            if not any(p.slot_id == active_slot_id for p in enabled_panels):
                active_slot_id = enabled_panels[0].slot_id
        else:
            active_slot_id = session_slots[0].slot_id if session_slots else 0

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

    def refresh_enabled_layout(self) -> None:
        """有効状態の変更後にレイアウトを再適用する.

        MainWindow が enable_slot / disable_slot を呼んだ後に使う。
        """
        self._apply_layout()

    def update_slot_checkbox(self, slot_id: int, enabled: bool) -> None:
        """チェックボックスの状態をプログラム的に更新する (シグナル抑制)."""
        if 0 <= slot_id < len(self._slot_checkboxes):
            cb = self._slot_checkboxes[slot_id]
            cb.blockSignals(True)
            cb.setChecked(enabled)
            cb.blockSignals(False)

    def update_slot_checkbox_label(self, slot_id: int, label: str) -> None:
        """チェックボックスのテキストを更新する."""
        if 0 <= slot_id < len(self._slot_checkboxes):
            self._slot_checkboxes[slot_id].setText(label)

    @property
    def active_slot_id(self) -> int:
        return self._active_slot_id

    @property
    def enabled_panel_count(self) -> int:
        return len(self._enabled_panels())

    # ================================================================
    # Internal — パネル検索
    # ================================================================

    def _find_panel(self, slot_id: int) -> Optional[SlotPanelWidget]:
        for p in self._panels:
            if p.slot_id == slot_id:
                return p
        return None

    def _enabled_panels(self) -> list[SlotPanelWidget]:
        """enabled なパネルだけを返す."""
        return [p for p in self._panels if p.is_enabled]

    # ================================================================
    # Internal — レイアウト
    # ================================================================

    def _apply_layout(self) -> None:
        """現在のレイアウト設定に従って enabled パネルを配置し直す."""
        # グリッドから全パネルを一旦外す
        for p in self._panels:
            self._grid.removeWidget(p)
            p.hide()

        # ストレッチをリセット
        for i in range(_MAX_GRID_DIM):
            self._grid.setRowStretch(i, 0)
            self._grid.setColumnStretch(i, 0)

        panels = self._enabled_panels()
        count = len(panels)
        if count == 0:
            return

        layout = self._current_layout
        used_rows = 0
        used_cols = 0

        if layout == "single":
            # アクティブスロットが enabled なら表示、そうでなければ最初の enabled
            target = self._active_slot_id
            target_panel = None
            for p in panels:
                if p.slot_id == target:
                    target_panel = p
                    break
            if target_panel is None:
                target_panel = panels[0]
            self._grid.addWidget(target_panel, 0, 0)
            target_panel.show()
            used_rows = 1
            used_cols = 1

        elif layout == "horizontal":
            for i, p in enumerate(panels):
                self._grid.addWidget(p, 0, i)
                p.show()
            used_rows = 1
            used_cols = count

        elif layout == "vertical":
            for i, p in enumerate(panels):
                self._grid.addWidget(p, i, 0)
                p.show()
            used_rows = count
            used_cols = 1

        elif layout == "grid_2x2":
            cols = 2
            for i, p in enumerate(panels):
                r = i // cols
                c = i % cols
                self._grid.addWidget(p, r, c)
                p.show()
            used_rows = (count + cols - 1) // cols
            used_cols = min(count, cols)

        else:
            for i, p in enumerate(panels):
                self._grid.addWidget(p, i, 0)
                p.show()
            used_rows = count
            used_cols = 1

        # 使用行列にストレッチ係数を設定
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

    def _on_slot_checkbox_toggled(self, slot_id: int, checked: bool) -> None:
        """ツールバーのスロットチェックボックスが切り替わった."""
        self.slot_enabled_changed.emit(slot_id, checked)

    @Slot()
    def _tick_preview(self) -> None:
        """全パネルのプレビューを更新する."""
        for p in self._panels:
            if p.isVisible():
                p.update_preview()
