#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from libs.CommandBase import CommandBase
from libs.keys import Button, Hat


class TableTurfAutoLose(CommandBase):
    NAME = "ナワバトラー自動敗北"
    CAPTURE_DIR = "./Screenshot/turf_war_loser/"
    TEMPLATE_PATH = "./template/turf_war_loser/"
    __tool_tip__ = "ナワバトラーを自動で負け続けます。" \
                   "対戦相手を選択後、デッキ選択画面で実行してください。"

    def __init__(self):
        super().__init__()

    def do(self):
        lose_count = 0
        loop_start_time = time.time()
        av_time = 0
        while True:
            st_time = time.time()
            end = False
            while not self.is_contain_template("start.png", threshold=0.8):
                self.press(Button.A)
                self.wait(4)
                if self.is_contain_template("pass.png", threshold=0.8):
                    self.press(Button.A)
                    self.wait(2)
                    break
            pass_count = 1
            while True:
                while not self.is_contain_template("pass.png", threshold=0.8):
                    if self.is_contain_template("lose.png", threshold=0.7):
                        # self.wait(2)
                        end = True
                        lose_count += 1
                        av_time = ((av_time * (lose_count - 1)) + time.time() - st_time) / lose_count
                        self.debug(f"負け {lose_count}回目")
                        self.debug(f"elapsed {time.time() - loop_start_time:.2f} sec")
                        self.debug(f"average {av_time:.2f} sec/loop")
                        break
                    self.press(Button.B)
                    self.wait(1)
                if not end:
                    self.press(Button.B)
                    # self.debug(f"パス {pass_count}回目")
                    self.press(Hat.BTM)
                    self.press(Hat.BTM)
                    self.press(Button.A)
                    self.press(Button.A)
                    pass_count += 1
                else:
                    break
