#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from libs.CommandBase import CommandBase
from libs.keys import Button


# Mash a button A
# A連打
class Mash_A(CommandBase):
    NAME = "A連打"
    CAPTURE_DIR = "./Screenshot"

    def __init__(self):
        super().__init__()

    def do(self):
        print(self.is_contain_template("a.png"))
        while True:
            self.wait(0.5)
            self.press(Button.A)
