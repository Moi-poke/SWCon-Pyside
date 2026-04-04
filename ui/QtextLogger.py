import logging

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QPlainTextEdit

import html
import logging

from PySide6 import QtWidgets
from PySide6.QtGui import QTextCursor


class QPlainTextEditLogger(logging.Handler):
    LEVEL_COLORS = {
        logging.DEBUG: "#9ca3af",  # 明るめグレー
        logging.INFO: "#38bdf8",  # 水色
        logging.WARNING: "#f59e0b",  # オレンジ
        logging.ERROR: "#f87171",  # 赤
        logging.CRITICAL: "#fb7185",  # 濃い赤
    }

    def __init__(self, parent):
        super().__init__()

        # HTML を使うので QTextEdit にする
        self.widget = QtWidgets.QTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setAcceptRichText(True)
        self.widget.setUndoRedoEnabled(False)
        self.widget.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        # ダークテーマ向けにログ欄だけ配色を固定
        self.widget.setStyleSheet("""
        QTextEdit {
            background-color: #1e1e1e;
            color: #d4d4d4;
            selection-background-color: #264f78;
            selection-color: #ffffff;
            border: 1px solid #3c3c3c;
            font-family: Consolas, 'Cascadia Mono', 'Meiryo UI', monospace;
            font-size: 10pt;
        }
        QScrollBar:vertical {
            background: #252526;
            width: 12px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #5a5a5a;
            min-height: 24px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #7a7a7a;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """)

    def emit(self, record):
        try:
            msg = self.format(record)

            # HTML 崩れ防止
            safe_msg = html.escape(msg).replace("\n", "<br>")

            color = self.LEVEL_COLORS.get(record.levelno, "#d4d4d4")

            self.widget.append(f'<span style="color:{color};">{safe_msg}</span>')

            # 常に末尾へスクロール
            cursor = self.widget.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.widget.setTextCursor(cursor)
            self.widget.ensureCursorVisible()

        except RuntimeError:
            # 終了時など、widget破棄後の emit を無視
            pass


class MyDialog(QtWidgets.QMdiSubWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        log_text_box = QPlainTextEditLogger(self)
        # You can format what is printed to text box
        log_text_box.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(log_text_box)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)

        self._button = QtWidgets.QPushButton(self)
        self._button.setText("Test Me")

        layout = QtWidgets.QVBoxLayout()
        # Add the new logging box widget to the layout
        layout.addWidget(log_text_box.widget)
        layout.addWidget(self._button)
        self.setLayout(layout)

        # Connect signal to slot
        self._button.clicked.connect(self.test)

    def test(self):
        logging.debug("damn, a bug")
        logging.info("something to remember")
        logging.warning("that's not right")
        logging.error("foobar")
