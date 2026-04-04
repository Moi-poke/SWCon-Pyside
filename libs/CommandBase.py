from __future__ import annotations

import enum
import logging
import os
import pathlib
import re
import threading
import time
import traceback
from abc import abstractmethod
from datetime import datetime
from typing import Any, Optional

import cv2
import numpy as np

try:
    import pykakasi
except Exception:
    pykakasi = None

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor

from libs.enums import ColorType
from libs.keys import Button, Direction, Hat


DEBUG = True


class StopThread(Exception):
    def __init__(self, result: bool, message: str = "") -> None:
        super().__init__(message)
        self.result = result


class CommandBase(QObject):
    print_strings = Signal(str, int)
    serial_input = Signal(object, float, float, object)
    stop_function = Signal(bool)
    recognize_rect = Signal(tuple, tuple, object, int)
    send_serial = Signal(str)

    # compatibility placeholders only
    get_image = Signal(bool)
    line_txt = Signal(str, str)
    line_img = Signal(str, str, object)

    CAPTURE_DIR = "./ScreenShot"
    TEMPLATE_PATH = "./template/"
    __directory__ = "./Commands/Python"
    __tool_tip__ = None
    __key__ = None

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._runtime_context = None
        self.__isCanceled = False
        self.__KeyBoardMode = None
        self.__KeyBoardMode_buff = None
        self.debug(f"コマンド実行Thread: {threading.get_ident()}")

    def set_runtime_context(self, context) -> None:
        self._runtime_context = context

    def __post_init__(self) -> None:
        return None

    def run(self) -> None:
        try:
            self.do()
            self.finish()
        except StopThread as exc:
            self.stop_function.emit(exc.result)
            self.info("Command finished successfully", force=True)
        except Exception as exc:
            traceback.print_exc()
            self.error(f"{exc} エラーが発生しました", force=True)
            self.stop_function.emit(True)

    @abstractmethod
    def do(self) -> None:
        raise NotImplementedError

    def _is_stop_requested(self) -> bool:
        if self.__isCanceled:
            return True
        if self._runtime_context is not None:
            return bool(self._runtime_context.is_stop_requested())
        return False

    def stop(self, signal: bool = True) -> None:
        self.__isCanceled = bool(signal)
        if self._runtime_context is not None and signal:
            self._runtime_context.request_stop()

    def finish(self) -> None:
        self.__isCanceled = True
        self.write_serial("end")
        raise StopThread(False, "finished")

    def press(
        self,
        buttons: Button | Hat | Direction | list[Button | Hat | Direction],
        duration: float = 0.1,
        wait: float = 0.1,
        repeat: int = 1,
        wo_wait: bool = False,
    ) -> None:
        if self._is_stop_requested():
            raise StopThread(False, "finished")

        if repeat > 1:
            for _ in range(repeat):
                self.serial_input.emit(buttons, duration, wait, "press")
                self.serial_input.emit(buttons, duration, wait, "release_all")
        else:
            if wo_wait:
                self.serial_input.emit(buttons, duration, wait, "press_w/o_wait")
            else:
                self.serial_input.emit(buttons, duration, wait, "press")
            self.wait(duration + wait)

    def release_all(self) -> None:
        self.serial_input.emit(None, 1, 1, "release_all")

    def pressRep(
        self,
        buttons: Button | Hat | Direction | list[Button | Hat | Direction],
        repeat: int,
        duration: float = 0.1,
        interval: float = 0.1,
        wait: float = 0.1,
    ) -> None:
        if self._is_stop_requested():
            raise StopThread(False, "finished")
        for i in range(repeat):
            self.press(buttons, duration, 0 if i == repeat - 1 else interval)
        self.wait(wait)

    def hold(
        self,
        buttons: Button | Hat | Direction | list[Button | Hat | Direction],
        duration: float = 0.1,
    ) -> None:
        if self._is_stop_requested():
            raise StopThread(False, "finished")
        self.serial_input.emit(buttons, duration, 0, "hold")

    def holdEnd(
        self,
        buttons: Button | Hat | Direction | list[Button | Hat | Direction],
    ) -> None:
        if self._is_stop_requested():
            raise StopThread(False, "finished")
        self.serial_input.emit(buttons, 0, 0, "hold end")

    def wait(self, wait_seconds: float) -> None:
        wait_s = max(float(wait_seconds), 0.0)
        end = time.perf_counter() + wait_s

        busy_threshold = 0.002  # 最後の2msだけbusy wait

        while True:
            if self._is_stop_requested():
                raise StopThread(True, "exit successfully")

            remain = end - time.perf_counter()
            if remain <= 0:
                return

            if remain > busy_threshold:
                time.sleep(max(remain - busy_threshold, 0.0))
            else:
                while time.perf_counter() < end:
                    if self._is_stop_requested():
                        raise StopThread(True, "exit successfully")
                return

    def check_if_alive(self) -> bool:
        if self._is_stop_requested():
            self.info("Exit from command successfully")
            raise StopThread(True, "exit successfully")
        return True

    def write_serial(self, s: str) -> None:
        self.send_serial.emit(s)

    @Slot(object)
    def callback_receive_img(self, frame: object) -> None:
        if isinstance(frame, np.ndarray):
            with self._frame_lock:
                self._latest_frame = frame.copy()
        else:
            with self._frame_lock:
                self._latest_frame = None

    def readFrame(self) -> Optional[np.ndarray]:
        if self._runtime_context is not None:
            return self._runtime_context.latest_frame_copy()
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def matching_image_in_the_template_listing(
        self,
        template_path_list: list[str],
        threshold: float = 0.7,
        use_gray: bool = False,
        show_value: bool = False,
        show_position: bool = False,
        show_rect_frame: bool = False,
        color: QColor = QColor(255, 0, 0, 127),
        trim: Optional[list[int]] = None,
    ) -> dict[str, dict[str, Any]]:
        src = self.readFrame()
        if src is None:
            self.warning("No latest frame available.")
            return {}

        color_mode = ColorType.GRAY if use_gray else ColorType.COLOR
        src_for_match = self.set_img_color_type(src, color_mode, 128)

        if trim is not None:
            src_for_match = src_for_match[trim[1] : trim[3], trim[0] : trim[2]]

        results: dict[str, dict[str, Any]] = {}

        for template_path in template_path_list:
            template = self.read_template(template_path)
            if template is None:
                results[template_path] = {"score": 0.0, "position": np.array([])}
                continue

            template = self.set_img_color_type(template, color_mode, 128)

            method = cv2.TM_CCOEFF_NORMED
            res = cv2.matchTemplate(src_for_match, template, method)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            w, h = template.shape[1], template.shape[0]
            positions = np.where(res >= threshold)
            scores = res[positions]

            boxes = []
            for y, x in zip(*positions):
                boxes.append([x, y, x + w - 1, y + h - 1])

            boxes_np = np.array(boxes) if boxes else np.empty((0, 4), dtype=int)
            boxes_np = self.non_max_suppression(boxes_np, scores, overlap_thresh=0.8)

            if show_value:
                self.debug(f"{template_path} ZNCC value: {max_val}")

            if show_position and show_rect_frame and len(boxes_np) > 0:
                for box in boxes_np:
                    top_left = (int(box[0]), int(box[1]))
                    bottom_right = (int(w + 1), int(h + 1))
                    if trim is not None:
                        top_left = (top_left[0] + trim[0], top_left[1] + trim[1])
                    self.send_template_matching_pos(
                        top_left, bottom_right, color, int(show_rect_frame)
                    )

            results[template_path] = {
                "score": float(max_val),
                "position": boxes_np,
            }

        return results

    def read_template(self, template_path: str) -> Optional[np.ndarray]:
        full_path = pathlib.Path(self.TEMPLATE_PATH) / template_path
        img = cv2.imread(str(full_path), cv2.IMREAD_COLOR)
        if img is None:
            self.error(f"テンプレート画像の読み込みに失敗しました: {full_path}")
        return img

    def is_contain_template(
        self,
        template_path: str | pathlib.Path,
        threshold: float = 0.7,
        use_gray: Optional[bool] = None,
        show_value: bool = False,
        show_position: bool = True,
        show_only_true_rect: bool = True,
        show_rect_frame: int = 120,
        color: QColor = QColor(255, 0, 0, 127),
        trim: Optional[list[int]] = None,
        color_mode: ColorType = ColorType.COLOR,
        binary_threshold: int = 128,
        show_template_name: str = "",
    ) -> bool:
        _ = (show_only_true_rect, show_template_name)

        if use_gray is not None:
            color_mode = ColorType.GRAY if use_gray else ColorType.COLOR

        src = self.readFrame()
        if src is None:
            self.warning("No latest frame available.")
            return False

        src = self.set_img_color_type(src, color_mode, binary_threshold)

        if trim is not None:
            src = src[trim[1] : trim[3], trim[0] : trim[2]]

        if isinstance(template_path, pathlib.Path):
            template_file = template_path
        else:
            template_file = pathlib.Path(self.TEMPLATE_PATH) / template_path

        template = cv2.imread(str(template_file), cv2.IMREAD_COLOR)
        if template is None:
            self.error(f"テンプレート画像の読み込みに失敗しました: {template_file}")
            return False

        template = self.set_img_color_type(template, color_mode, binary_threshold)

        w, h = template.shape[1], template.shape[0]
        res = cv2.matchTemplate(src, template, cv2.TM_CCOEFF_NORMED)
        positions = np.where(res >= threshold)
        scores = res[positions]

        boxes = []
        for y, x in zip(*positions):
            boxes.append([x, y, x + w - 1, y + h - 1])
        boxes_np = np.array(boxes) if boxes else np.empty((0, 4), dtype=int)
        boxes_np = self.non_max_suppression(boxes_np, scores, overlap_thresh=0.8)

        _, max_val, _, _ = cv2.minMaxLoc(res)
        if show_value:
            self.debug(f"{template_path} ZNCC value: {max_val}")

        bottom_right = (w + 1, h + 1)

        if max_val >= threshold:
            if show_position:
                for i in range(len(boxes_np)):
                    if trim is not None:
                        top_left = (
                            int(boxes_np[i][0] + trim[0]),
                            int(boxes_np[i][1] + trim[1]),
                        )
                    else:
                        top_left = (int(boxes_np[i][0]), int(boxes_np[i][1]))
                    self.send_template_matching_pos(
                        top_left, bottom_right, color, show_rect_frame
                    )

                if trim is not None:
                    self.send_template_matching_pos(
                        (trim[0], trim[1]),
                        (trim[2] - trim[0], trim[3] - trim[1]),
                        QColor(0, 255, 0, 255),
                        show_rect_frame,
                    )
            return True

        if show_position and trim is not None:
            self.send_template_matching_pos(
                (trim[0], trim[1]),
                (trim[2] - trim[0], trim[3] - trim[1]),
                QColor(0, 255, 0, 255),
                show_rect_frame,
            )
        return False

    def set_img_color_type(self, src, color_mode, binary_threshold):
        if src is None:
            raise ValueError("Input image is None")

        match color_mode:
            case ColorType.COLOR:
                # すでに BGR 相当ならそのまま返す
                if len(src.shape) == 2:
                    return cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)
                if len(src.shape) == 3 and src.shape[2] == 4:
                    return cv2.cvtColor(src, cv2.COLOR_BGRA2BGR)
                return src

            case ColorType.GRAY:
                if len(src.shape) == 2:
                    return src
                if len(src.shape) == 3 and src.shape[2] == 4:
                    return cv2.cvtColor(src, cv2.COLOR_BGRA2GRAY)
                return cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

            case ColorType.BINARY:
                if len(src.shape) == 2:
                    gray = src
                elif len(src.shape) == 3 and src.shape[2] == 4:
                    gray = cv2.cvtColor(src, cv2.COLOR_BGRA2GRAY)
                else:
                    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

                _, binary = cv2.threshold(
                    gray, binary_threshold, 255, cv2.THRESH_BINARY
                )
                return binary

            case _:
                raise Exception("Color setting failed")

    @staticmethod
    def non_max_suppression(
        boxes: np.ndarray, scores: np.ndarray, overlap_thresh: float
    ) -> np.ndarray:
        if len(boxes) <= 1:
            return boxes

        boxes = boxes.astype("float")
        x1, y1, x2, y2 = np.squeeze(np.split(boxes, 4, axis=1))
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        indices = np.argsort(scores)
        selected = []

        while len(indices) > 0:
            last = len(indices) - 1
            selected_index = indices[last]
            remaining_indices = indices[:last]
            selected.append(selected_index)

            if len(remaining_indices) == 0:
                break

            i_x1 = np.maximum(x1[selected_index], x1[remaining_indices])
            i_y1 = np.maximum(y1[selected_index], y1[remaining_indices])
            i_x2 = np.minimum(x2[selected_index], x2[remaining_indices])
            i_y2 = np.minimum(y2[selected_index], y2[remaining_indices])

            i_w = np.maximum(0, i_x2 - i_x1 + 1)
            i_h = np.maximum(0, i_y2 - i_y1 + 1)
            overlap = (i_w * i_h) / area[remaining_indices]

            indices = np.delete(
                indices,
                np.concatenate(([last], np.where(overlap > overlap_thresh)[0])),
            )

        return boxes[selected].astype("int")

    def send_template_matching_pos(self, top_left, bottom_right, color, frames) -> None:
        self.recognize_rect.emit(top_left, bottom_right, color, frames)

    def screenshot(self) -> None:
        frame = self.readFrame()
        if frame is None:
            self.warning("No latest frame available for screenshot.")
            return

        try:
            path = (
                pathlib.Path(self.CAPTURE_DIR)
                / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            self.image_write(path, frame)
            self.info(f"capture succeeded: {path}")
        except cv2.error as exc:
            self.error(f"Capture failed: {exc}")

    def line_notify(
        self, txt: Any, token_key: str = "token_1", img: Optional[bool] = None
    ) -> None:
        _ = (txt, token_key, img)
        self.warning("line_notify() was ignored because LineNotify is omitted.")

    @staticmethod
    def image_write(filename: str | pathlib.Path, img, params=None) -> bool:
        try:
            ext = os.path.splitext(str(filename))[1]
            result, n = cv2.imencode(ext, img, params)
            if result:
                with open(filename, mode="w+b") as f:
                    n.tofile(f)
                return True
            return False
        except Exception:
            return False

    def debug(self, s: Any, force: bool = False) -> None:
        if force or not self._is_stop_requested():
            msg = f"thread id={threading.get_ident()} {s}"
            self.print_strings.emit(msg, logging.DEBUG)

    def info(self, s: Any, force: bool = False) -> None:
        if force or not self._is_stop_requested():
            msg = f"thread id={threading.get_ident()} {s}"
            self.print_strings.emit(msg, logging.INFO)

    def warning(self, s: Any, force: bool = False) -> None:
        if force or not self._is_stop_requested():
            msg = f"thread id={threading.get_ident()} {s}"
            self.print_strings.emit(msg, logging.WARNING)

    def error(self, s: Any, force: bool = False) -> None:
        if force or not self._is_stop_requested():
            msg = f"thread id={threading.get_ident()} {s}"
            self.print_strings.emit(msg, logging.ERROR)

    def critical(self, s: Any, force: bool = False) -> None:
        if force or not self._is_stop_requested():
            msg = f"thread id={threading.get_ident()} {s}"
            self.print_strings.emit(msg, logging.CRITICAL)

    def keyboard_init(self) -> None:
        self.__KeyBoardMode = 0
        self.__KeyBoardMode_buff = 0
        self.write_serial("end")
        self.wait(0.05)

    def type_string_roman(self, send_str: str) -> None:
        self.write_serial(f'"{send_str}"')

    def type_string(self, text: str, conversion: bool = False) -> None:
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

    def type_string_ln(self, text: str, conversion: bool = False) -> None:
        self.type_string(text, conversion)
        self.type_key(KEY.ENTER)

    def type_password_local(self, password: str) -> bool:
        status = re.search(r"^[0-9]+$", password)
        if status is None:
            return False
        self.type_string_roman(password)
        self.wait(0.1 * len(password))
        return True

    def type_password_online(self, password: str) -> bool:
        pw = password.lower()
        status = re.search(r"^[0-9qwertyupasdfghjklxcvbnm]+$", pw)
        if status is None:
            return False
        self.type_string_roman(pw)
        self.wait(0.1 * len(pw))
        return True

    def type_key(self, key_value, show_value: bool = False) -> None:
        if show_value:
            self.debug(KEY(key_value).name)
        self.write_serial(f"Key {int(key_value)}")

    def press_key(self, key_value, show_value: bool = False) -> None:
        if show_value:
            self.debug(KEY(key_value).name)
        self.write_serial(f"Press {int(key_value)}")

    def release_key(self, key_value, show_value: bool = False) -> None:
        if show_value:
            self.debug(KEY(key_value).name)
        self.write_serial(f"Release {int(key_value)}")

    def reset_password(self) -> None:
        self.press_key(KEY.BACKSPACE)
        self.wait(0.6)
        self.release_key(KEY.BACKSPACE)

    def reset_controller(self) -> None:
        self.write_serial("3 8 80 80 80 80")

    @staticmethod
    def debug_log(text) -> None:
        if DEBUG:
            print(text)

    @staticmethod
    def split_by_character_type(text):
        txt = text
        result_list = []
        pattern_list = [
            r"^[\u3040-\u309F]+",
            r"^[\u30A0-\u30FB\u30FD-\u30FF]+",
            r"^[a-zA-Z0-9\-!@#\$%\^&\*\(\)_~`=\\\+\{\}\[\]<>;:\"',\./\?]+",
            r"^[ー～「」、。・]+",
        ]
        i = 0
        while i < len(pattern_list):
            status = re.search(pattern_list[i], txt)
            if status is not None:
                txt = txt[status.span()[1] :]
                result_list.append([status.group(), i])
                i = 0
                continue
            i += 1
        return result_list

    def convert_to_roman(self, splitlist):
        roman_list = []
        for item in splitlist:
            roman_list.append([self.convert_to_roman_sub(item[0], item[1]), item[1]])
        return roman_list

    @staticmethod
    def convert_to_roman_sub(text, mode):
        if mode == KeyboardMode.DOUBLEBYTESYMBOL:
            convert_map = {
                "ー": "-",
                "～": "~",
                "「": "[",
                "」": "]",
                "、": ",",
                "。": ".",
                "・": "/",
            }
            txt = ""
            for ch in text:
                txt += convert_map[ch]
            return txt

        if pykakasi is None:
            return text

        kks = pykakasi.kakasi()
        if mode == KeyboardMode.HIRAGANA:
            kks.setMode("H", "a")
        elif mode == KeyboardMode.KATAKANA:
            kks.setMode("K", "a")
        else:
            return text

        return kks.convert(text)[0]["kunrei"]

    def change_keyboard_mode(self, mode):
        if (self.__KeyBoardMode == KeyboardMode.HIRAGANA) and (
            mode == KeyboardMode.KATAKANA
        ):
            self.type_key(KEY.JP_HIRAGANA)
        elif (self.__KeyBoardMode == KeyboardMode.HIRAGANA) and (
            mode == KeyboardMode.ALPHANUMERIC_SYMBOL
        ):
            self.type_key(KEY.JP_HANZEN)
        elif (self.__KeyBoardMode == KeyboardMode.KATAKANA) and (
            mode == KeyboardMode.HIRAGANA
        ):
            self.type_key(KEY.JP_HIRAGANA)
        elif (self.__KeyBoardMode == KeyboardMode.KATAKANA) and (
            mode == KeyboardMode.ALPHANUMERIC_SYMBOL
        ):
            self.type_key(KEY.JP_HIRAGANA)
            self.type_key(KEY.JP_HANZEN)
        elif (self.__KeyBoardMode == KeyboardMode.ALPHANUMERIC_SYMBOL) and (
            mode == KeyboardMode.HIRAGANA
        ):
            self.type_key(KEY.JP_HANZEN)
        elif (self.__KeyBoardMode == KeyboardMode.ALPHANUMERIC_SYMBOL) and (
            mode == KeyboardMode.KATAKANA
        ):
            self.type_key(KEY.JP_HANZEN)
            self.type_key(KEY.JP_HIRAGANA)
        elif (self.__KeyBoardMode == KeyboardMode.ALPHANUMERIC_SYMBOL) and (
            mode == KeyboardMode.DOUBLEBYTESYMBOL
        ):
            self.type_key(KEY.JP_HANZEN)
            self.__KeyBoardMode = KeyboardMode.HIRAGANA
            return
        else:
            self.__KeyBoardMode = mode
            self.__KeyBoardMode_buff = mode
            return

        self.__KeyBoardMode = mode
        self.__KeyBoardMode_buff = mode


class KeyboardMode(enum.IntEnum):
    HIRAGANA = 0
    KATAKANA = 1
    ALPHANUMERIC_SYMBOL = 2
    DOUBLEBYTESYMBOL = 3


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
    JP_HENKAN = 0x8A
