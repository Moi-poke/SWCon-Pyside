#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logging import getLogger, DEBUG, NullHandler

from Commands.CommandBase import CommandBase


# ログ出力のサンプル
class LoggingSample(CommandBase):
    NAME = 'ログ出力のサンプル'

    def __init__(self):
        super().__init__()

    def do(self):
        self.debug("DEBUG")
        self.info("INFO")
        self.warning("WARNING")
        self.error("ERROR")
        self.critical("CRITICAL")
