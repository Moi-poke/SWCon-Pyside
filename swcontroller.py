from __future__ import annotations

import logging
import os
import sys

import PySide6
from PySide6.QtWidgets import QApplication

from mainwindow import MainWindow


def main() -> int:
    logger = logging.getLogger(__name__)

    dirname = os.path.dirname(PySide6.__file__)
    plugin_path = os.path.join(dirname, "plugins", "platforms")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

    try:
        with open("ui/style.qss", "r", encoding="utf-8") as f:
            style = f.read()
    except Exception:
        style = ""

    try:
        app = QApplication(sys.argv)
        app.setStyleSheet(style)
        window = MainWindow()
        window.show()
        return app.exec()
    except Exception as e:
        logger.exception(e)
        print("quit")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
