from __future__ import annotations

import logging
from logging import NullHandler, getLogger
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal


class LineNotify(QObject):
    """
    Deprecated compatibility shim.

    LINE Notify はサービス終了前提のため、本クラスは何も送信しない。
    既存コードが import / instantiate しても落ちないように残している。
    """

    print_strings = Signal(str, int)

    def __init__(self, tokens: Optional[dict[str, str]] = None) -> None:
        super().__init__()
        self.logger = getLogger(__name__)
        self.logger.addHandler(NullHandler())
        self.logger.propagate = True
        self.token_list = tokens if isinstance(tokens, dict) else {}
        self._warn_deprecated()

    def _warn_deprecated(self) -> None:
        message = "[LINE] LineNotify is omitted because the service is no longer used."
        self.print_strings.emit(message, logging.WARNING)

    @staticmethod
    def is_utf8_file_with_bom(filename: str) -> bool:
        try:
            line_first = open(filename, encoding="utf-8").readline()
            return bool(line_first and line_first[0] == "\ufeff")
        except Exception:
            return False

    def __str__(self) -> str:
        return "LineNotify(no-op shim)"

    @classmethod
    def retrieve_line_instance(cls, token: dict[str, str]) -> "LineNotify":
        return cls(tokens=token)

    def send_text(self, notification_message: Any, token_key: str) -> None:
        _ = (notification_message, token_key)
        self.print_strings.emit(
            "[LINE] send_text() was ignored because LineNotify is omitted.",
            logging.WARNING,
        )

    def send_text_n_image(
        self, img: Any, notification_message: Any, token_key: str
    ) -> None:
        _ = (img, notification_message, token_key)
        self.print_strings.emit(
            "[LINE] send_text_n_image() was ignored because LineNotify is omitted.",
            logging.WARNING,
        )

    def get_rate_limit(self) -> None:
        self.print_strings.emit(
            "[LINE] get_rate_limit() was ignored because LineNotify is omitted.",
            logging.WARNING,
        )
