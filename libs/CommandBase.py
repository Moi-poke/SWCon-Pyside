import enum
import logging
import os
import pathlib
import random
import re
import threading
import time
import traceback
from abc import abstractmethod
from datetime import datetime
from typing import Optional

import cv2
import numpy
import numpy as np
import pykakasi
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QPainter

from libs.enums import ColorType
from libs.keys import Button, Hat, Direction
from concurrent.futures import ThreadPoolExecutor

DEBUG = True


class StopThread(Exception):
    pass


class CommandBase(QObject):
    """Python Commandの基底クラス

    Args:
        QObject (_type_): QThreadにいれるObject
    """

    print_strings = Signal(str, type(logging.DEBUG))
    serial_input = Signal(type(Button.A), float, float, str)
    stop_function = Signal(bool)
    get_image = Signal(bool)
    recognize_rect = Signal(tuple, tuple, QColor, int)
    line_txt = Signal(str, str)
    line_img = Signal(str, str, np.ndarray)
    send_serial = Signal(str)

    CAPTURE_DIR = "./ScreenShot"
    TEMPLATE_PATH = "./template/"
    __directory__ = "./Commands/Python"
    __tool_tip__ = None
    __key__ = None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.wait_ret = None
        self.__src = None
        self.__isCanceled = False
        self.debug(f"コマンド実行Thread: {threading.get_ident()}")
        self.__KeyBoardMode = None
        self.__KeyBoardMode_buff = None
        # print("init")

    def __post_init__(self):
        """
        init後、run実行前に実行される処理。
        スクリプトリロード時に処理させたい内容
        情報表示など
        """
        ...

    def run(self):
        # ここでdo()を行えばよいはず?
        try:
            self.do()
            self.finish()
        except StopThread as e:
            self.stop_function.emit(True)
            self.info("Command finished successfully", force=True)
        except Exception as e:
            # self.error(e)
            traceback.print_exc()
            self.error(f"{e} エラーが発生しました", force=True)
            self.stop_function.emit(True)
            # raise StopThread
            pass
        finally:
            pass
            # self.release_all() # 接続切れてるので意味無し
        # if self.isCanceled:
        #     self.debug("Command Stopped.", force=True)
        # self.info("Command finished successfully", force=True)
        # self.stop_function.emit(False)

    @abstractmethod  # 抽象化：継承した際に定義必須
    def do(self):
        pass

    def stop(self, signal=True):
        self.__isCanceled = signal
        # self.stop_function.emit(True)
        # if self.thread_do and shiboken6.isValid(self.thread_do):
        #     if self.thread_do.isRunning() or not self.thread_do.isFinished():
        #         # self.worker.stop()
        #         # self.thread_do.quit()
        #         # self.thread_do.wait()
        #         self.parent.pushButton_PythonStart.setEnabled(True)

    def finish(self):
        self.__isCanceled = True
        self.write_serial("end")
        self.stop_function.emit(False)
        raise StopThread

    def press(self,
              buttons: Button | Hat | Direction | list[Button | Hat | Direction],
              duration: float = 0.1,
              wait: float = 0.1,
              repeat: int = 1,
              wo_wait: bool = False):
        """

        Args:
            buttons: 各ボタン/方向キー/スティック
            duration: 押下時間
            wait: 押したあとの待機時間
            repeat: 繰り返し回数
            wo_wait: 連続した入力を前提としたpress, inputEnd処理を挟みません。
        """
        if not self.__isCanceled:
            if repeat > 1:
                for _ in range(0, repeat):
                    self.serial_input.emit(buttons, duration, wait, "press")
                    # self.wait(wait)
                self.serial_input.emit(buttons, duration, wait, "release_all")
                # self.wait(wait)
            elif repeat == 1:
                if wo_wait is False:
                    self.serial_input.emit(buttons, duration, wait, "press")
                    self.wait(duration + wait)
                else:
                    self.serial_input.emit(buttons, duration, wait, "press_w/o_wait")
                    self.wait(duration + wait)
        else:
            raise StopThread

    def release_all(self):
        self.serial_input.emit(None, 1, 1, "release_all")

    def pressRep(self, buttons: Button | Hat | Direction | list[Button | Hat | Direction],
                 repeat: int, duration: float = 0.1, interval: float = 0.1, wait: float = 0.1):
        if not self.__isCanceled:
            for _ in range(0, repeat):
                self.press(buttons, duration, 0 if _ == repeat - 1 else interval)
            self.wait(wait)
        else:
            raise StopThread

    def hold(self, buttons: Button | Hat | Direction | list[Button | Hat | Direction],
             duration: float = 0.1):
        if not self.__isCanceled:
            self.serial_input.emit(buttons, duration, 0, "hold")
        else:
            raise StopThread

    def holdEnd(self, buttons: Button | Hat | Direction | list[Button | Hat | Direction]):
        if not self.__isCanceled:
            self.serial_input.emit(buttons, 0, 0, "hold end")
        else:
            raise StopThread

    def wait(self, wait: float):
        self.wait_ret = False
        # if float(wait) > 0.1 and not self.isCanceled:
        #     time.sleep(0.1)
        #     self.wait(wait - 0.1)
        # else:
        #     current_time = time.perf_counter()
        #     while time.perf_counter() < current_time + wait:
        #         if not self.isCanceled:
        #             # print(time.perf_counter())
        #             pass
        #         else:
        #             raise StopThread
        if self.__isCanceled:
            return
        elif float(wait) > 0.1:
            time.sleep(wait)
        else:
            current_time = time.perf_counter()
            while time.perf_counter() < current_time + wait:
                pass

    def check_if_alive(self) -> bool:
        if self.__isCanceled:
            # raise exception for exit working thread
            self.info("Exit from command successfully")
            # self.stop_function.emit(True)
            raise StopThread("exit successfully")
        else:
            return True

    def write_serial(self, s: str):
        self.send_serial.emit(s)

    # Get image from main thread and return src
    def readFrame(self):
        self.get_image.emit(True)
        return self.__src

    def matching_image_in_the_template_listing(
            self,
            template_path_list: list[str],
            threshold: float = 0.7,
            use_gray: bool = False,
            show_value: bool = False,
            show_position: bool = False,
            show_rect_frame: bool = False,
            color: QColor = QColor(255, 0, 0, 127),
            trim: Optional[list[int, int, int, int]] = None
    ) -> dict:
        """

        Args:
            template_path_list: テンプレートパス(str)のリスト
            threshold:
            use_gray:
            show_value:
            show_position:
            show_rect_frame:
            color:
            trim: left_up_x, left_up_y, right_down_x, right_down_y

        Returns:

        """

        def get_res(targets) -> dict:
            _src = targets[0]
            _path = targets[1]
            _img = targets[2]
            _method = cv2.TM_CCOEFF_NORMED

            _res = cv2.matchTemplate(_src, _img, _method)
            _, max_val, _, max_loc = cv2.minMaxLoc(_res)

            w, h = _img.shape[1], _img.shape[0]

            positions = np.where(_res >= threshold)
            scores = _res[positions]
            boxes = []
            for y, x in zip(*positions):
                boxes.append([x, y, x + w - 1, y + h - 1])
            boxes = np.array(boxes)
            # print(boxes)
            boxes = self.non_max_suppression(boxes, scores, overlap_thresh=0.8)

            return {_path: {"score": max_val, "position": boxes}}

        self.get_image.emit(True)
        src = cv2.cvtColor(self.__src, cv2.COLOR_BGR2GRAY) if use_gray else self.__src
        if trim is not None:
            src = src[trim[1]:trim[3], trim[0]:trim[2]]

        results_1 = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            res = executor.map(self.read_template, [[s, use_gray] for s in template_path_list], timeout=None)
            for _ in res:
                results_1.append(_)

        args = [[src, i[0], i[1]] for i in results_1]
        results_2 = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            res = executor.map(get_res, args)
            for _ in res:
                results_2 |= _

        return results_2

    def read_template(self, *args) -> list:
        # print(*args)
        template_path: str = args[0][0]
        use_gray: bool = args[0][1]
        return [template_path,
                cv2.imread(self.TEMPLATE_PATH + template_path, cv2.IMREAD_GRAYSCALE if use_gray else cv2.IMREAD_COLOR)]

    def is_contain_template(
            self,
            template_path: str | pathlib.Path,
            threshold=0.7,
            use_gray: bool | None = None,
            show_value: bool = False,
            show_position: bool = True,
            show_only_true_rect: bool = True,
            show_rect_frame: int = 120,
            color: QColor = QColor(255, 0, 0, 127),
            trim: Optional[list[int, int, int, int]] = None,
            color_mode: ColorType = ColorType.COLOR,
            binary_threshold: int = 128,
            show_template_name: str = ""
    ) -> bool:
        """

        Args:
            template_path: テンプレートのパス
            threshold: 閾値
            use_gray: グレーで画像認識
            show_value: 一致度
            show_position: どこでみつかったか
            show_only_true_rect: 見つかった箇所のみ枠を表示
            show_rect_frame: 枠を表示
            color: QColor, 枠の色
            trim: left_up_x, left_up_y, right_down_x, right_down_y
            show_template_name: show Template image name
            binary_threshold: threshold at binary
            color_mode: Template Match Color Settings

        Returns:

        """
        if use_gray is not None:
            if use_gray:
                color_mode = ColorType.GRAY
            elif not use_gray:
                color_mode = ColorType.COLOR

        self.get_image.emit(True)

        src = self.set_img_color_type(self.__src, color_mode, binary_threshold)

        if trim is not None:
            src = src[trim[1]:trim[3], trim[0]:trim[2]]

        if type(template_path) == str:
            template = self.set_img_color_type(cv2.imread(self.TEMPLATE_PATH) + template_path, color_mode, binary_threshold)
        elif isinstance(template_path, pathlib.Path):
            template = self.set_img_color_type(cv2.imread((str(template_path))), color_mode, binary_threshold)
        else:
            template = None

        if template is not None:
            w, h = template.shape[1], template.shape[0]
        else:
            self.error("テンプレート画像の読み込みに失敗しました")
            return False

        method = cv2.TM_CCOEFF_NORMED
        res = cv2.matchTemplate(src, template, method)

        positions = np.where(res >= threshold)
        scores = res[positions]
        boxes = []
        for y, x in zip(*positions):
            boxes.append([x, y, x + w - 1, y + h - 1])
        boxes = np.array(boxes)
        # print(boxes)
        boxes = self.non_max_suppression(boxes, scores, overlap_thresh=0.8)
        # print(boxes)

        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if show_value:
            print(template_path + " ZNCC value: " + str(max_val))

        top_left = max_loc
        # self.bottom_right = (self.top_left[0] + w + 1, self.top_left[1] + h + 1)
        bottom_right = (w + 1, h + 1)
        # print(self.top_left)
        # print(self.bottom_right)
        top_lefts = []
        bottom_rights = []
        for i in range(box_n := len(boxes)):
            if trim is not None:
                top_lefts.append((boxes[i][0] + trim[0], boxes[i][1] + trim[1]))
            else:
                top_lefts.append((boxes[i][0], boxes[i][1]))
            # bottom_rights.append((boxes[i][2], boxes[i][3]))
        # tag = str(time.perf_counter()) + str(random.random())
        if max_val >= threshold:
            if show_position:
                for i in range(box_n):
                    self.send_template_matching_pos(top_lefts[i], bottom_right,
                                                    color, show_rect_frame)
                if trim is not None:
                    self.send_template_matching_pos((trim[0], trim[1]), (trim[2] - trim[0], trim[3] - trim[1]),
                                                    QColor(0, 255, 0, 255), show_rect_frame)
            return True
        else:
            if show_position:
                if trim is not None:
                    self.send_template_matching_pos((trim[0], trim[1]), (trim[2] - trim[0], trim[3] - trim[1]),
                                                    QColor(0, 255, 0, 255), show_rect_frame)
            return False

    def set_img_color_type(self, src, color_mode, binary_threshold):
        match color_mode:
            case ColorType.COLOR:
                # colorならsourceは変更しない
                pass
            case ColorType.GRAY:
                src = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
            case ColorType.BINARY:
                src = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
                ret, src = cv2.threshold(src, binary_threshold, 255, cv2.THRESH_BINARY)
            case _:
                raise Exception('Color setting failed')
        return src

    @staticmethod
    def non_max_suppression(boxes: np.ndarray, scores: np.ndarray, overlap_thresh: float) -> np.ndarray:
        """
        https://pystyle.info/opencv-non-maximum-suppression/ を参考にしました。
        Non Maximum Suppression (NMS) を行う。

        Args:
            scores: 画像認識の結果(一致率)
            boxes: (N, 4) の numpy 配列。矩形の一覧。
            overlap_thresh: [0, 1] の実数。閾値。

        Returns:
            boxes : (M, 4) の numpy 配列。Non Maximum Suppression により残った矩形の一覧。
        """
        if len(boxes) <= 1:
            return boxes

        # float 型に変換する。
        boxes = boxes.astype("float")

        # (NumBoxes, 4) の numpy 配列を x1, y1, x2, y2 の一覧を表す4つの (NumBoxes, 1) の numpy 配列に分割する。
        x1, y1, x2, y2 = np.squeeze(np.split(boxes, 4, axis=1))

        # 矩形の面積を計算する。
        area = (x2 - x1 + 1) * (y2 - y1 + 1)

        indices = np.argsort(scores)  # スコアを降順にソートしたインデックス一覧
        selected = []  # NMS により選択されたインデックス一覧

        # indices がなくなるまでループする。
        while len(indices) > 0:
            # indices は降順にソートされているので、最後の要素の値 (インデックス) が
            # 残っている中で最もスコアが高い。
            last = len(indices) - 1

            selected_index = indices[last]
            remaining_indices = indices[:last]
            selected.append(selected_index)

            # 選択した短形と残りの短形の共通部分の x1, y1, x2, y2 を計算する。
            i_x1 = np.maximum(x1[selected_index], x1[remaining_indices])
            i_y1 = np.maximum(y1[selected_index], y1[remaining_indices])
            i_x2 = np.minimum(x2[selected_index], x2[remaining_indices])
            i_y2 = np.minimum(y2[selected_index], y2[remaining_indices])

            # 選択した短形と残りの短形の共通部分の幅及び高さを計算する。
            # 共通部分がない場合は、幅や高さは負の値になるので、その場合、幅や高さは 0 とする。
            i_w = np.maximum(0, i_x2 - i_x1 + 1)
            i_h = np.maximum(0, i_y2 - i_y1 + 1)

            # 選択した短形と残りの短形の Overlap Ratio を計算する。
            overlap = (i_w * i_h) / area[remaining_indices]

            # 選択した短形及び Overlap Ratio が閾値以上の短形を indices から削除する。
            indices = np.delete(
                indices, np.concatenate(([last], np.where(overlap > overlap_thresh)[0]))
            )

        # 選択された短形の一覧を返す。
        return boxes[selected].astype("int")

    def send_template_matching_pos(self, top_left, bottom_right, color, frames):
        self.recognize_rect.emit(top_left, bottom_right, color, frames)
        pass

    @Slot(numpy.ndarray)
    def callback_receive_img(self, frame):
        self.__src = frame

    def screenshot(self):
        try:
            self.get_image.emit(True)
            self.image_write(
                pathlib.Path(self.CAPTURE_DIR) / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png", self.__src
            )
            print("capture succeeded:")
            pass
        except cv2.error as e:
            # print("Capture Failed")
            pass

    # ログをメインに飛ばすため
    def debug(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.DEBUG)

    def info(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.INFO)

    def warning(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.WARNING)

    def error(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.ERROR)

    def critical(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.CRITICAL)

    def line_notify(self, txt: any, token_key: str = "token_1", img: Optional[bool] = None) -> None:
        if not img:
            self.line_txt.emit(txt, token_key)
        else:
            self.get_image.emit(True)
            self.line_img.emit(txt, token_key, self.__src)

    @staticmethod
    def image_write(filename: str | pathlib.Path, img, params=None) -> bool:
        try:
            # print(img)
            ext = os.path.splitext(filename)[1]
            result, n = cv2.imencode(ext, img, params)

            if result:
                with open(filename, mode="w+b") as f:
                    n.tofile(f)
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return False

    ######################################################################################################
    '''
    作:ろっこく 氏(Twitter @Rokkoku_I)
    '''

    # ここから

    # キーボードの初期化関数(キーボード画面が表示されたときに1度だけ実行すること)
    def keyboard_init(self):
        """
        キーボードの初期化関数(キーボード画面が表示されたときに1度だけ実行すること)
        """
        self.__KeyBoardMode = 0
        self.__KeyBoardMode_buff = 0
        self.write_serial('end')
        self.wait(0.05)

    # キーボード入力
    def type_string_roman(self, send_str):
        # print('入力文字列:' + send_str)
        send_str = '"' + send_str + '"'
        self.write_serial(send_str)

    # キーボードによる文字列入力(改行なし)
    def type_string(self, text, conversion=False):
        """
        キーボードによる文字列入力(改行なし)

        Parameters
        ----------
        text : str        キーボードで入力したい文字列
        ----------
        conversion : bool        キーボードによる変換機能付きかどうか
        """
        print('入力文字列:' + text)
        text = text.replace("ん", "んん")
        text = text.replace("ン", "ンン")
        splitlist = self.split_by_character_type(text)
        self.debug_log(splitlist)
        roman_list = self.convert_to_roman(splitlist)
        self.debug_log(roman_list)
        for roman_item in roman_list:
            self.change_keyboard_mode(roman_item[1])
            self.type_string_roman(roman_item[0])
            self.wait(0.1 * len(roman_item[0]))
            if conversion:
                self.type_key(KEY.ENTER)
        self.wait(0.5)
        self.press(Button.PLUS)

    # キーボードによる文字列入力(改行あり)
    def type_string_ln(self, text, conversion=False):
        """
        キーボードによる文字列入力(改行あり)

        Parameters
        ----------
        text : str        キーボードで入力したい文字列
        ----------
        conversion : bool        キーボードによる変換機能付きかどうか
        """
        self.type_string(text, conversion)
        self.type_key(KEY.ENTER)

    # パスワード入力(ローカルレイド)
    def type_password_local(self, password):
        """
        パスワード入力(ローカルレイド)

        Parameters
        ----------
        password : str
        パスワード(0-9の文字列)
        """
        status = re.search('^[0-9]+$', password)
        if status is None:
            print('TypePassWord_Local:不正な引数です。(' + password + ')')
            return False
        print('パスワード:' + password)
        self.type_string_roman(password)
        self.wait(0.1 * len(password))
        return True

    # パスワード入力(オンラインレイド)
    def type_password_online(self, password):
        """
        パスワード入力(ローカルレイド)

        Parameters
        ----------
        password : str        パスワード(「0-9QWERTYUPASDFGHJKLXCVBNM」の文字列)
        """
        pw = password.lower()
        status = re.search('^[0-9qwertyupasdfghjklxcvbnm]+$', pw)
        if status is None:
            print('TypePassWord_Online:不正な引数です。(' + password + ')')
            return False
        print('パスワード:' + password)
        self.type_string_roman(pw)
        self.wait(0.1 * len(pw))
        return True

    # キー入力
    def type_key(self, key_value, show_value=False):
        """
        キー入力

        Parameters
        ----------
        key_value : int        キーボードで入力したいキー
        ----------
        show_value : bool        入力したキーの値をprintするか
        """
        if show_value:
            print(KEY(key_value).name)
        send_str = 'Key ' + str(int(key_value))
        self.write_serial(send_str)

    # キーを押しっぱなしにする
    def press_key(self, key_value, show_value=False):
        """
        キーを押しっぱなしにする

        Parameters
        ----------
        key_value : int        押しっぱなしにしたいキー
        ----------
        show_value : bool        入力したキーの値をprintするか
        """
        if show_value:
            print(KEY(key_value).name)
        send_str = 'Press ' + str(int(key_value))
        self.write_serial(send_str)

    # 押しっぱなしにしているキーを離す
    def release_key(self, key_value, show_value=False):
        """
        押しっぱなしにしているキーを離す

        Parameters
        ----------
        key_value : int        離したいキー
        ----------
        show_value : bool        入力したキーの値をprintするか
        """
        if show_value:
            print(KEY(key_value).name)
        send_str = 'Release ' + str(int(key_value))
        self.write_serial(send_str)

    # 入力したパスワードをリセットする
    def reset_password(self):
        self.press_key(KEY.BACKSPACE)
        self.wait(0.1 * 6)  # 0.1sec × (削除したい文字数)が待機時間の目安
        self.release_key(KEY.BACKSPACE)

    # コントローラーを無入力状態に戻す
    def reset_controller(self):
        self.write_serial('3 8 80 80 80 80')

    # デバッグ用のlogを残す関数
    @staticmethod
    def debug_log(text):
        if DEBUG:
            print(text)

    ######################################################################################################
    '''
    キーボード系
    '''

    # 文字種に応じて文字列を分割する
    @staticmethod
    def split_by_character_type(text):
        txt = text
        result_list = []
        pattern_list = [
            # 【参考】文字コード:https://0g0.org/category/3040-309F/1/
            '^[\u3040-\u309F]+',  # ひらがな u+3040 - u+309F
            '^[\u30A0-\u30FB\u30FD-\u30FF]+',  # カタカナ u+30A0 - u+30FF(【除】「ー」:u+30FC)
            # '^[\u30A0-\u30FF]+', # カタカナ u+30A0 - u+30FF
            '^[a-zA-Z0-9\-!@#\$%\^&\*\(\)_~`=\\\+\{\}\|\[\]<>;:"\',\.\?/]+',  # 英数字・記号
            '^[ー～「」、。・]+'  # 全角記号
        ]
        i = 0
        while i < len(pattern_list):
            status = re.search(pattern_list[i], txt)
            if status is not None:
                txt = txt[status.span()[1]:]
                str_list_tmp = [status.group(), i]
                result_list.append(str_list_tmp)
                i = 0
                continue
            i = i + 1
        return result_list

    # ローマ字に変換する
    def convert_to_roman(self, splitlist):
        roman_list = []
        for item in splitlist:
            roman_list_tmp = [self.convert_to_roman_sub(item[0], item[1]), item[1]]
            roman_list.append(roman_list_tmp)
        return roman_list

    # ローマ字に変換する
    @staticmethod
    def convert_to_roman_sub(text, mode):
        kks = pykakasi.kakasi()
        if mode == KeyboardMode.HIRAGANA:
            kks.setMode("H", "a")  # default: Hiragana -> Roman
        elif mode == KeyboardMode.KATAKANA:
            kks.setMode("K", "a")  # default: Katakana -> Roman
        elif mode == KeyboardMode.DOUBLEBYTESYMBOL:
            txt = ''
            double_byte_symbol_convert_list = {
                'ー': '-',
                '～': '~',
                '「': '[',
                '」': ']',
                '、': ',',
                '。': '.',
                '・': '/'
            }
            for i in range(len(text)):
                txt = txt + double_byte_symbol_convert_list[text[i]]
            return txt
        else:
            return text
        return kks.convert(text)[0]['kunrei']  # hepburn/kunrei/passport

    def change_keyboard_mode(self, mode):
        if (self.__KeyBoardMode == KeyboardMode.HIRAGANA) and (mode == KeyboardMode.KATAKANA):
            self.type_key(KEY.JP_HIRAGANA)
        elif (self.__KeyBoardMode == KeyboardMode.HIRAGANA) and (mode == KeyboardMode.ALPHANUMERIC_SYMBOL):
            self.type_key(KEY.JP_HANZEN)
        elif (self.__KeyBoardMode == KeyboardMode.KATAKANA) and (mode == KeyboardMode.HIRAGANA):
            self.type_key(KEY.JP_HIRAGANA)
        elif (self.__KeyBoardMode == KeyboardMode.KATAKANA) and (mode == KeyboardMode.ALPHANUMERIC_SYMBOL):
            self.type_key(KEY.JP_HIRAGANA)
            self.type_key(KEY.JP_HANZEN)
        elif (self.__KeyBoardMode == KeyboardMode.ALPHANUMERIC_SYMBOL) and (mode == KeyboardMode.HIRAGANA):
            self.type_key(KEY.JP_HANZEN)
        elif (self.__KeyBoardMode == KeyboardMode.ALPHANUMERIC_SYMBOL) and (mode == KeyboardMode.KATAKANA):
            self.type_key(KEY.JP_HANZEN)
            self.type_key(KEY.JP_HIRAGANA)
        elif (self.__KeyBoardMode == KeyboardMode.ALPHANUMERIC_SYMBOL) and (mode == KeyboardMode.DOUBLEBYTESYMBOL):
            self.type_key(KEY.JP_HANZEN)
            self.__KeyBoardMode = KeyboardMode.HIRAGANA
            return
        else:
            return
        self.__KeyBoardMode = mode
        self.__KeyBoardMode_buff = mode


######################################################################################################
# キーボードのかな/カナ/英字を管理するためのクラス
class KeyboardMode(enum.IntEnum):
    HIRAGANA = 0  # ひらがな
    KATAKANA = 1  # カタカナ
    ALPHANUMERIC_SYMBOL = 2  # 英数字
    DOUBLEBYTESYMBOL = 3  # 全角記号


# キーコードを管理するためのクラス
class KEY(enum.IntEnum):
    SPACE = 32
    ENTER = 40
    BACKSPACE = 42
    DELETE = 76
    UP_ARROW = 79
    DOWN_ARROW = 80
    LEFT_ARROW = 81
    RIGHT_ARROW = 82
    JP_HANZEN = 0x35
    JP_BACKSLASH = 0x87
    JP_HIRAGANA = 0x88
    # JP_YEN			= 0x89	#「￥」:Switchでは非対応？
    JP_HENKAN = 0x8A

# JP_MUHENKAN	= 0x8B	#無変換:Switchでは非対応？

# ここまで
######################################################################################################
