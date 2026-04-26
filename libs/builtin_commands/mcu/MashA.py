#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from libs.mcu_command_base import McuCommand


# Mash A button
class Mash_A(McuCommand):
    NAME = "A連打"

    def __init__(self, sync_name="mash_a"):
        super().__init__(sync_name)
