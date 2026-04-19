"""SlotPanelWidget — 1スロット分のUI パネル."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QImage, QMouseEvent, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from libs.session_slot import SessionSlot

logger = logging.getLogger(__name__)

# アクティブ枠のスタイル
_ACTIVE_STYLE = "SlotPanelWidget { border: 2px solid #2979FF; }"
_INACTIVE_STYLE = "SlotPanelWidget { border: 2px solid transparent; }"


# ────────────────────────────────────────────────────────────────
# paintEvent で描画するプレビュー専用ウィジェット
#
# ・QLabel.setPixmap() は sizeHint を pixmap サイズに更新し、
#   レイアウト→縮小→setPixmap→さらに縮小 のフィードバックループを起こす。
# ・paintEvent で直接描画すれば sizeHint に影響を与えず安全。
# ・キャプチャ解像度を超える拡大も行い、ウィジェット領域を最大限活用する。
# ────────────────────────────────────────────────────────────────
class _PreviewWidget(QWidget):
    """アスペクト比を保って QPixmap を描画する軽量ウィジェット.

    ウィジェットがキャプチャ解像度より大きい場合でも拡大して描画する。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )

        # 背景色
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), Qt.GlobalColor.black)
        self.setPalette(pal)

    # -- public --
    def set_pixmap(self, pixmap: QPixmap) -> None:
        """描画する pixmap をセットし、再描画を要求する."""
        self._pixmap = pixmap
        self.update()

    def current_pixmap(self) -> Optional[QPixmap]:
        return self._pixmap

    # -- override --
    def minimumSizeHint(self) -> QSize:  # noqa: N802
        """最小サイズヒントを返す (0,0 でレイアウトに一任)."""
        return QSize(0, 0)

    def sizeHint(self) -> QSize:  # noqa: N802
        """デフォルト希望サイズ (参考値)."""
        return QSize(640, 360)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        """リサイズ時に再描画を強制する."""
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        """アスペクト比を保ちつつ、ウィジェット領域内で最大サイズに描画する.

        キャプチャ解像度がウィジェットより小さくても拡大して表示する。
        """
        if self._pixmap is None or self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        pw = self._pixmap.width()
        ph = self._pixmap.height()

        if pw <= 0 or ph <= 0:
            painter.end()
            return

        # ウィジェットのアスペクト比と画像のアスペクト比を比較し、
        # アスペクト比を保ったまま最大サイズを計算する
        widget_ratio = w / h
        pixmap_ratio = pw / ph

        if pixmap_ratio >= widget_ratio:
            # 横長 or 一致 → 幅に合わせる
            draw_w = w
            draw_h = int(w / pixmap_ratio)
        else:
            # 縦長 → 高さに合わせる
            draw_h = h
            draw_w = int(h * pixmap_ratio)

        # 中央に配置
        x = (w - draw_w) // 2
        y = (h - draw_h) // 2

        painter.drawPixmap(x, y, draw_w, draw_h, self._pixmap)
        painter.end()


class SlotPanelWidget(QFrame):
    """1スロット分のプレビュー + 操作UIパネル."""

    # ---- signals ----
    activated = Signal(int)                     # slot_id
    start_requested = Signal(int)               # slot_id
    stop_requested = Signal(int)                # slot_id
    camera_change_requested = Signal(int, int)  # slot_id, camera_id
    com_port_change_requested = Signal(int, str)  # slot_id, port

    def __init__(
        self,
        slot_id: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._slot_id = slot_id
        self._session_slot: Optional[SessionSlot] = None
        self._is_active = False
        self._last_preview_seq: int = 0
        self._camera_list: list[dict] = []

        self.setObjectName("SlotPanelWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(_INACTIVE_STYLE)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )

        self._build_ui()

    # ================================================================
    # UI構築
    # ================================================================

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(2)

        # ---- ヘッダー行: ラベル + ステータス (固定高さ) ----
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(f"Slot {self._slot_id}")
        self._label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self._label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed,
        )
        header.addWidget(self._label)

        self._serial_status = QLabel("Serial: —")
        self._serial_status.setStyleSheet("color: gray; font-size: 11px;")
        self._serial_status.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed,
        )
        header.addStretch()
        header.addWidget(self._serial_status)
        root.addLayout(header, stretch=0)

        # ---- プレビュー (paintEvent で描画、残り全スペースを使う) ----
        self._preview = _PreviewWidget()
        root.addWidget(self._preview, stretch=1)

        # ---- コマンドステータス + ボタン行 (固定高さ) ----
        cmd_row = QHBoxLayout()
        cmd_row.setContentsMargins(0, 0, 0, 0)
        self._cmd_status = QLabel("Idle")
        self._cmd_status.setStyleSheet("font-size: 11px;")
        self._cmd_status.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        cmd_row.addWidget(self._cmd_status, stretch=1)

        self._btn_start = QPushButton("▶")
        self._btn_start.setFixedWidth(40)
        self._btn_start.setToolTip("コマンド開始")
        self._btn_start.clicked.connect(
            lambda: self.start_requested.emit(self._slot_id)
        )
        cmd_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("⏹")
        self._btn_stop.setFixedWidth(40)
        self._btn_stop.setToolTip("コマンド停止")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(
            lambda: self.stop_requested.emit(self._slot_id)
        )
        cmd_row.addWidget(self._btn_stop)
        root.addLayout(cmd_row, stretch=0)

        # ---- デバイス行: カメラ + COM (固定高さ) ----
        dev_row = QHBoxLayout()
        dev_row.setContentsMargins(0, 0, 0, 0)

        self._combo_camera = QComboBox()
        self._combo_camera.setToolTip("カメラ選択")
        self._combo_camera.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        self._combo_camera.currentIndexChanged.connect(self._on_camera_changed)
        dev_row.addWidget(self._combo_camera, stretch=2)

        self._edit_com = QLineEdit()
        self._edit_com.setPlaceholderText("COM Port")
        self._edit_com.setToolTip("COMポート (例: COM3)")
        self._edit_com.setMaximumWidth(100)
        self._edit_com.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed,
        )
        self._edit_com.editingFinished.connect(self._on_com_changed)
        dev_row.addWidget(self._edit_com, stretch=1)

        root.addLayout(dev_row, stretch=0)

    # ================================================================
    # Public API
    # ================================================================

    @property
    def slot_id(self) -> int:
        return self._slot_id

    @property
    def preview_label(self) -> _PreviewWidget:
        """プレビューウィジェットを返す (型が _PreviewWidget に変更)."""
        return self._preview

    def bind_session_slot(self, session_slot: SessionSlot) -> None:
        """SessionSlot をバインドし、ラベルを更新する."""
        self._session_slot = session_slot
        self._label.setText(session_slot.config.display_label())
        if session_slot.config.com_port:
            self._edit_com.setText(session_slot.config.com_port)

    def set_camera_list(self, camera_list: list[dict]) -> None:
        """カメラ一覧をセットする."""
        self._camera_list = camera_list
        self._combo_camera.blockSignals(True)
        self._combo_camera.clear()
        for cam in camera_list:
            label = f"{cam['index']}: {cam['name']}"
            self._combo_camera.addItem(label)
        self._combo_camera.blockSignals(False)

    def select_camera(self, camera_id: int) -> None:
        """カメラIDに対応するコンボボックスアイテムを選択する."""
        self._combo_camera.blockSignals(True)
        for i, cam in enumerate(self._camera_list):
            if int(cam["index"]) == camera_id:
                self._combo_camera.setCurrentIndex(i)
                break
        self._combo_camera.blockSignals(False)

    def set_com_port(self, port: str) -> None:
        self._edit_com.setText(port)

    def update_preview(self) -> None:
        """FrameStore から新しいフレームがあれば取得し、プレビューを更新する.

        描画は _PreviewWidget.paintEvent() が担当。
        リサイズ時の再描画も resizeEvent → update() で自動処理する。
        """
        if self._session_slot is None:
            return
        if not self._session_slot.config.enabled:
            return

        image, seq = self._session_slot.frame_store.get_preview_if_new(
            self._last_preview_seq,
        )
        if image is not None:
            self._last_preview_seq = seq
            self._preview.set_pixmap(QPixmap.fromImage(image))

    def set_serial_status(self, opened: bool, label: str) -> None:
        if opened:
            self._serial_status.setText(f"Serial: {label}")
            self._serial_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self._serial_status.setText("Serial: —")
            self._serial_status.setStyleSheet("color: gray; font-size: 11px;")

    def set_command_status(self, running: bool, name: str = "") -> None:
        if running:
            self._cmd_status.setText(f"Running: {name}")
            self._cmd_status.setStyleSheet("color: #2979FF; font-size: 11px;")
        else:
            self._cmd_status.setText("Idle")
            self._cmd_status.setStyleSheet("color: gray; font-size: 11px;")
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    def set_active(self, active: bool) -> None:
        """アクティブスロットの枠ハイライトを切り替える."""
        self._is_active = active
        self.setStyleSheet(_ACTIVE_STYLE if active else _INACTIVE_STYLE)

    # ================================================================
    # Internal
    # ================================================================

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """クリックでアクティブスロットを切り替える."""
        self.activated.emit(self._slot_id)
        super().mousePressEvent(event)

    def _on_camera_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._camera_list):
            return
        cam_id = int(self._camera_list[index]["index"])
        self.camera_change_requested.emit(self._slot_id, cam_id)

    def _on_com_changed(self) -> None:
        port = self._edit_com.text().strip()
        self.com_port_change_requested.emit(self._slot_id, port)
