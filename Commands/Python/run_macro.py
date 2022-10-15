#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

from libs.CommandBase import CommandBase
from libs.keys import Button
import datetime


class RunMacro(CommandBase):
    NAME = "マクロ実行テスト"
    CAPTURE_DIR = "./Macro/"
    __tool_tip__ = "記録したマクロを実行したい"

    def __init__(self):
        super().__init__()

    def __post_init__(self):
        ...

    def do(self):
        filename = "./macro/hogehoge.log"
        # macroフォルダに起動中に操作した履歴が保存されていくので、それをいい感じにする。
        try:
            with open(filename) as f:
                macro_ls: list[datetime, str] = []
                while line := f.readline():
                    ln = line.rstrip().split(",")
                    ln[0] = datetime.datetime.strptime(ln[0], '%Y-%m-%d %H:%M:%S.%f')
                    macro_ls.append(ln)
            # self.debug(macro_ls)
            for i in range((len_macro := len(macro_ls)) - 1):
                self.debug(macro_ls[i])
                start = time.perf_counter()
                wait = (abs(macro_ls[i + 1][0] - macro_ls[i][0]).total_seconds())
                self.write_serial(macro_ls[i][1])
                self.wait(wait - (time.perf_counter() - start))
            # self.write_serial()
        except:
            pass
