#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 必要なライブラリをimportしてください
from libs.CommandBase import CommandBase
from libs.keys import Button, Hat, Direction, Stick


class Tutorial(CommandBase):  # 複数のスクリプトでClass名が重複することは避けてください。また、CommandBaseの継承は必須です。
    NAME = "Readme"  # スクリプトの表示名
    CAPTURE_DIR = "./Readme/"  # スクリプトを選択時にスクリーンショットボタンを押下した際の保存先
    TEMPLATE_PATH = "./template/"  # スクリプト内で画像認識を行うときの画像参照先
    __tool_tip__ = "いろんな動作のサンプル(WIP)"  # ←の文字列がスクリプトをコンボボックスで選択時に表示されます。

    """
    class変数を定義する際はここで定義しましょう。
    なお、下記変数名は予約済なので、使用しないでください
    __directory__
    print_strings
    serial_input
    stop_function
    get_image
    recognize_rect
    line_txt
    line_img
    send_serial    
    """

    def __init__(self):
        super().__init__()
        """
        インスタンス変数を定義する際はここで定義するようにしましょう。

        なお、下記変数名は予約済なので、使用を控えてください
        self.src
        self.isCanceled    
        """

    def __post_init__(self) -> None:
        """
        initが呼ばれるタイミングではGUIへの文字出力ができないため、
        Poke Controllerで行われていた起動時の情報表示をinitに記載してもできません。
        もし必要であれば__post_init__()内で処理してください。
        """
        ...

    def do(self) -> None:
        """
        GUI内 STARTボタンを押下時に呼ばれる関数です。
        記法など詳細はgithub wikiを参照ください
        https://github.com/Moi-poke/SWCon-Pyside/wiki
        """
        self.debug(f"このスクリプトは何も行いません。")
        ...
