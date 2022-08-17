#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from libs.keys import Button
from Commands.CommandBase import CommandBase


# Mash a button A
# A連打
class Mash_A(CommandBase):
    NAME = 'A連打'

    def __init__(self):
        super().__init__()

    def do(self):
        while True:
            self.wait(0.5)
            self.press(Button.A)
