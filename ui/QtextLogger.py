import logging

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QPlainTextEdit


class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.appendPlainText("")

    def emit(self, record):
        msg = self.format(record)
        msg = msg.replace("\n", "<br>")
        # self.widget.appendPlainText(msg)
        if "ERROR" in str(msg) or "CRITICAL" in str(msg) or "FATAL" in str(msg):
            self.widget.appendHtml(f"<span style=\"color:#ff0000;\" > {msg} </span>")
        else:
            self.widget.appendHtml(f"<span style=\"color:#000000;\" > {msg} </span>")


class MyDialog(QtWidgets.QMdiSubWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        log_text_box = QPlainTextEditLogger(self)
        # You can format what is printed to text box
        log_text_box.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
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
