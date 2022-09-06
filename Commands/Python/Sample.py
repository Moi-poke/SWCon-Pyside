#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib

from PySide6.QtGui import QColor

from libs.CommandBase import CommandBase
from libs.keys import Button


# Mash a button A
# A連打
class Mash_A(CommandBase):
    NAME = "Sample"
    CAPTURE_DIR = "./Screenshot/"
    __directory__ = __file__

    def __init__(self):
        super().__init__()
        # print(__file__)

    def do(self):
        for i in range(1):
            # 画像認識テスト
            self.debug(
                self.is_contain_template(
                    "a.png", threshold=0.95, show_rect_frame=120, trim=[10, 10, 630, 710], color=QColor(255, 0, 0, 255)
                )
            )
            self.wait(0.02)
        # while True:
        #     self.wait(0.5)
        #     self.press(Button.A)
