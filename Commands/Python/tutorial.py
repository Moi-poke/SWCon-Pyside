#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from libs.CommandBase import CommandBase
from libs.keys import Button


# Mash a button A
# A連打
class Tutorial(CommandBase):
    NAME = "ちゅーとりある？"
    CAPTURE_DIR = "./Screenshot/"
    __tool_tip__ = "いろんな動作のサンプル(WIP)"

    def __init__(self):
        super().__init__()

    def __post_init__(self):
        self.debug("do()より前になにか処理をしたいときは、'__post_init__'の中でしましょう")

    def do(self):
        self.debug(self.is_contain_template("a.png", threshold=0.9, trim=[50, 50, 500, 500]))
        # 以下は与えたリスト内と画像認識するやつ
        self.debug(self.matching_image_in_the_template_listing(
            ["a.png", "a.png", "a.png", "a.png", "a.png", "a.png", "a.png"], trim=[700, 200, 900, 350]))
        # self.line_notify("test", img=True)
        # while True:
        #     self.wait(0.5)
        #     self.press(Button.A)
