#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import datetime
import logging
import math
import os
import platform
import time
from logging import NullHandler, getLogger
from pathlib import Path
from typing import Optional

import serial
from PySide6.QtCore import QObject, Signal


class Sender(QObject):
    """
    Pure serial sender utility.

    Notes
    -----
    - ライブラリ側では StreamHandler を勝手に追加しない
    - エラーは握り潰さず、log signal + 例外再送出で上位へ伝える
    - 本クラス単体よりも SerialWorker 経由で使うことを推奨
    """

    print_strings = Signal(str, int)

    def __init__(self, is_show_serial: bool, if_print: bool = True) -> None:
        super().__init__()

        self.ser: Optional[serial.Serial] = None
        self.is_show_serial = bool(is_show_serial)
        self.is_print = bool(if_print)

        self._logger = getLogger(__name__)
        self._logger.addHandler(NullHandler())
        self._logger.propagate = True

        self.f: Optional[object] = None
        self.before: Optional[str] = None

        self.L_holding = False
        self._L_holding: Optional[float] = None
        self.R_holding = False
        self._R_holding: Optional[float] = None

        self.time_bef = time.perf_counter()
        self.time_aft = time.perf_counter()

        self.Buttons = [
            "Stick.RIGHT",
            "Stick.LEFT",
            "Button.Y",
            "Button.B",
            "Button.A",
            "Button.X",
            "Button.L",
            "Button.R",
            "Button.ZL",
            "Button.ZR",
            "Button.MINUS",
            "Button.PLUS",
            "Button.LCLICK",
            "Button.RCLICK",
            "Button.HOME",
            "Button.CAPTURE",
        ]
        self.Hat = [
            "TOP",
            "TOP_RIGHT",
            "RIGHT",
            "BTM_RIGHT",
            "BTM",
            "BTM_LEFT",
            "LEFT",
            "TOP_LEFT",
            "CENTER",
        ]

    # ------------------------------------------------------------------
    # serial open / close
    # ------------------------------------------------------------------
    def openSerial(self, port_num: int | str, port_name: str = "") -> bool:
        """
        Open serial port.

        Returns
        -------
        bool
            True on success

        Raises
        ------
        serial.SerialException, OSError
            when opening port fails
        """
        self.closeSerial(silent=True)

        resolved = self._resolve_port_name(port_num, port_name)
        if not resolved:
            self.warning("Not supported OS or invalid port setting.")
            return False

        self.info(f"Connecting to {resolved}")
        try:
            self.ser = serial.Serial(resolved, 9600, timeout=1)
            self._open_log_file()
            return True
        except (serial.SerialException, OSError) as exc:
            self.error(f"COM Port can't be established: {exc}")
            self.closeSerial(silent=True)
            raise

    def closeSerial(self, silent: bool = False) -> None:
        if not silent:
            self.debug("Closing the serial communication")

        if self.ser is not None:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception as exc:
                if not silent:
                    self.warning(f"Serial close raised exception: {exc}")
            finally:
                self.ser = None

        if self.f is not None:
            try:
                self.f.close()
            except Exception as exc:
                if not silent:
                    self.warning(f"Log file close raised exception: {exc}")
            finally:
                self.f = None

        self.before = None

    def _is_open_no_log(self) -> bool:
        return bool(self.ser is not None and self.ser.is_open)

    def isOpened(self) -> bool:
        self.debug("Checking if serial communication is open")
        return bool(self.ser is not None and self.ser.is_open)

    # ------------------------------------------------------------------
    # write
    # ------------------------------------------------------------------
    def writeRow(self, row: str, is_show: bool = False) -> None:
        if not self._is_open_no_log():
            message = "Using a port that is not open."
            self.error(message)
            raise RuntimeError(message)

        try:
            self.time_bef = time.perf_counter()

            if self.before is not None and self.before != "end" and is_show:
                output = self.before.split(" ")
                self.show_input(output)

            assert self.ser is not None
            self.ser.write((row + "\r\n").encode("utf-8"))
            self.time_aft = time.perf_counter()

            if self.is_show_serial and row != "0x0000 8" and row != self.before:
                self.debug(row)

            if row != self.before:
                self._write_log_line(row)
                self.before = row

        except (serial.SerialException, OSError) as exc:
            self.error(f"Serial write failed: {exc}")
            raise
        except Exception as exc:
            self.error(f"Unexpected serial write error: {exc}")
            raise

    # ------------------------------------------------------------------
    # helper
    # ------------------------------------------------------------------
    def _resolve_port_name(self, port_num: int | str, port_name: str) -> Optional[str]:
        if port_name:
            return str(port_name)

        if os.name == "nt":
            return f"COM{port_num}"

        if os.name == "posix":
            if platform.system() == "Darwin":
                return f"/dev/tty.usbserial-{port_num}"
            return f"/dev/ttyUSB{port_num}"

        return None

    def _open_log_file(self) -> None:
        macro_dir = Path("./macro")
        macro_dir.mkdir(parents=True, exist_ok=True)
        log_path = macro_dir / f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.log"
        self.f = open(log_path, "w", encoding="utf-8")

    def _write_log_line(self, row: str) -> None:
        if self.f is None:
            return
        self.f.write(
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')},{row}\n"
        )
        self.f.flush()

    # ------------------------------------------------------------------
    # debug formatter for reverse logging
    # ------------------------------------------------------------------
    def show_input(self, output: list[str]) -> None:
        """
        Best-effort reverse formatter for sent serial data.
        旧実装の膨大な print 群を整理し、logger 向けの簡易表現に縮退。
        """
        try:
            btns = [
                self.Buttons[x] for x in range(0, 16) if int(output[0], 16) >> x & 1
            ]
            hat = self.Hat[int(output[1])]
            if hat != "CENTER":
                btns = btns + [f"Hat.{hat}"]

            l_stick = list(map(lambda x: int(x, 16), output[2:4]))
            r_stick = list(map(lambda x: int(x, 16), output[4:]))

            l_deg = math.degrees(math.atan2(128 - l_stick[1], l_stick[0] - 128))
            r_deg = math.degrees(math.atan2(128 - r_stick[1], r_stick[0] - 128))

            summary = f"btns={btns}, L={l_stick}@{l_deg:.0f}, R={r_stick}@{r_deg:.0f}"
            if self.is_print:
                self.debug(summary)
        except Exception as exc:
            self.warning(f"show_input parse failed: {exc}")

    # ------------------------------------------------------------------
    # log helpers
    # ------------------------------------------------------------------
    def debug(self, s: str, force: bool = False) -> None:
        self.print_strings.emit(s, logging.DEBUG)

    def info(self, s: str, force: bool = False) -> None:
        self.print_strings.emit(s, logging.INFO)

    def warning(self, s: str, force: bool = False) -> None:
        self.print_strings.emit(s, logging.WARNING)

    def error(self, s: str, force: bool = False) -> None:
        self.print_strings.emit(s, logging.ERROR)

    def critical(self, s: str, force: bool = False) -> None:
        self.print_strings.emit(s, logging.CRITICAL)
