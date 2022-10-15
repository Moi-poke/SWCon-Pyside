import logging
import os
import pathlib
import random
import threading
import time
from abc import abstractmethod
from datetime import datetime
from typing import Optional

import cv2
import numpy
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QPainter

from libs.keys import Button
from concurrent.futures import ThreadPoolExecutor


class StopSignal(Exception):
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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.src = None
        self.isCanceled = False
        self.debug(f"コマンド実行Thread: {threading.get_ident()}")
        # print("init")

    def __post_init__(self):
        ...

    def run(self):
        # ここでdo()を行えばよいはず?
        try:
            self.do()
        except StopSignal as e:
            self.stop_function.emit(True)
            self.info("Command finished successfully")
        # except ZeroDivisionError:
        #     self.error(111, force=True)
        except Exception as e:
            self.error(e)
            self.error("エラーが発生しました", force=True)
            self.stop_function.emit(True)
            # raise StopSignal
            pass
        if self.isCanceled:
            self.debug("Command Stopped.", force=True)
        self.stop_function.emit(True)

    @abstractmethod  # 抽象化：継承した際に定義必須
    def do(self):
        pass

    def stop(self, signal=True):
        self.isCanceled = signal
        # self.stop_function.emit(True)
        # if self.thread_do and shiboken6.isValid(self.thread_do):
        #     if self.thread_do.isRunning() or not self.thread_do.isFinished():
        #         # self.worker.stop()
        #         # self.thread_do.quit()
        #         # self.thread_do.wait()
        #         self.parent.pushButton_PythonStart.setEnabled(True)

    def finish(self):
        self.isCanceled = True
        raise StopSignal

    def press(self, buttons, duration: float = 0.1, wait: float = 0.1):
        if not self.isCanceled:
            self.serial_input.emit(buttons, duration, wait, "press")
        else:
            raise StopSignal

    def pressRep(self, buttons, repeat: int, duration: float = 0.1, wait: float = 0.1, interval: float = 0.1):
        if not self.isCanceled:
            for _ in range(repeat):
                self.press(buttons, duration, wait)
                self.wait(interval)
        else:
            raise StopSignal

    def hold(self, buttons, duration: float = 0.1):
        if not self.isCanceled:
            self.serial_input.emit(buttons, duration, "hold")
        else:
            raise StopSignal

    def holdEnd(self, buttons):
        if not self.isCanceled:
            self.serial_input.emit(buttons, "hold end")
        else:
            raise StopSignal

    def wait(self, wait: float):
        if float(wait) > 0.1 and not self.isCanceled:
            time.sleep(wait)
        else:
            current_time = time.perf_counter()
            while time.perf_counter() < current_time + wait:
                if not self.isCanceled:
                    pass
                else:
                    raise StopSignal

    def check_if_alive(self) -> bool:
        if self.isCanceled:
            # raise exception for exit working thread
            self.info("Exit from command successfully")
            # self.stop_function.emit(True)
            raise StopSignal("exit successfully")
        else:
            return True

    def write_serial(self, s: str):
        self.send_serial.emit(s)

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
        src = cv2.cvtColor(self.src, cv2.COLOR_BGR2GRAY) if use_gray else self.src
        if trim is not None:
            src = src[trim[1]:trim[3], trim[0]:trim[2]]

        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            res = executor.map(self.read_template, [[s, use_gray] for s in template_path_list], timeout=None)
            for _ in res:
                results.append(_)

        args = [[src, i[0], i[1]] for i in results]
        results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            res = executor.map(get_res, args)
            for _ in res:
                results |= _

        return results

    def read_template(self, *args) -> list:
        # print(*args)
        template_path: str = args[0][0]
        use_gray: bool = args[0][1]
        return [template_path,
                cv2.imread(self.TEMPLATE_PATH + template_path, cv2.IMREAD_GRAYSCALE if use_gray else cv2.IMREAD_COLOR)]

    def is_contain_template(
            self,
            template_path: str,
            threshold=0.7,
            use_gray: bool = False,
            show_value: bool = False,
            show_position: bool = True,
            show_only_true_rect: bool = True,
            show_rect_frame: int = 120,
            color: QColor = QColor(255, 0, 0, 127),
            trim: Optional[list[int, int, int, int]] = None
    ) -> bool:
        """

        Args:
            template_path: テンプレートのパスを入力
            threshold: 閾値
            use_gray: グレー状態で処理する
            show_value:
            show_position:
            show_only_true_rect:
            show_rect_frame:
            color:
            trim: left_up_x, left_up_y, right_down_x, right_down_y

        Returns:

        """
        self.get_image.emit(True)
        src = cv2.cvtColor(self.src, cv2.COLOR_BGR2GRAY) if use_gray else self.src
        if trim is not None:
            src = src[trim[1]:trim[3], trim[0]:trim[2]]
        template = cv2.imread(
            self.TEMPLATE_PATH + template_path, cv2.IMREAD_GRAYSCALE if use_gray else cv2.IMREAD_COLOR
        )
        w, h = template.shape[1], template.shape[0]

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
        tag = str(time.perf_counter()) + str(random.random())
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

    @staticmethod
    def non_max_suppression(boxes, scores, overlap_thresh):
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
        self.src = frame

    def screenshot(self):
        try:
            self.get_image.emit(True)
            self.imwrite(
                pathlib.Path(self.CAPTURE_DIR) / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png", self.src
            )
            print("capture succeeded:")
            pass
        except cv2.error as e:
            # print("Capture Failed")
            pass

    # ログをメインに飛ばすため
    def debug(self, s, force=False):
        if force or not self.isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.DEBUG)

    def info(self, s, force=False):
        if force or not self.isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.INFO)

    def warning(self, s, force=False):
        if force or not self.isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.WARNING)

    def error(self, s, force=False):
        if force or not self.isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.ERROR)

    def critical(self, s, force=False):
        if force or not self.isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.CRITICAL)

    def line_notify(self, txt, token_key="token_1", img: Optional[bool] = None) -> None:
        if not img:
            self.line_txt.emit(txt, token_key)
        else:
            self.get_image.emit(True)
            self.line_img.emit(txt, token_key, self.src)

    @staticmethod
    def imwrite(filename, img, params=None) -> bool:
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
