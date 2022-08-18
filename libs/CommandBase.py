import logging
import os
import random
import threading
import time
from abc import abstractmethod

import cv2
import numpy
from PySide6.QtCore import QObject, Signal, Slot

from libs.keys import Button


class StopSignal(Exception):
    pass


class CommandBase(QObject):
    """Python Commandの基底クラス

    Args:
        QObject (_type_): QThreadにいれるObject
    """

    print_strings = Signal(str, type(logging.DEBUG))
    serial_input = Signal(type(Button.A), float, float)
    stop_function = Signal(bool)
    get_image = Signal(bool)

    CAPTURE_DIR = "./ScreenShot"
    TEMPLATE_PATH = "./template/"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.src = None
        self.isCanceled = False
        self.debug(f"コマンド実行Thread: {threading.get_ident()}")

    def run(self):
        # ここでdo()を行えばよいはず?
        try:
            self.do()
        except StopSignal:
            self.info("Command finished successfully")
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

    def press(self, buttons, duration=0.1, wait=0.1):
        if not self.isCanceled:
            self.serial_input.emit(buttons, duration, wait)
        else:
            raise StopSignal

    def wait(self, wait):
        if float(wait) > 0.1 and not self.isCanceled:
            time.sleep(wait)
        else:
            current_time = time.perf_counter()
            while time.perf_counter() < current_time + wait:
                if not self.isCanceled:
                    pass
                else:
                    raise StopSignal

    def check_if_alive(self):
        if self.isCanceled:
            # raise exception for exit working thread
            self.info("Exit from command successfully")
            # self.stop_function.emit(True)
            raise StopSignal("exit successfully")
        else:
            return True

    def is_contain_template(
        self,
        template_path,
        threshold=0.7,
        use_gray=False,
        show_value=False,
        show_position=True,
        show_only_true_rect=True,
        ms=2000,
    ):
        self.get_image.emit(True)
        src = cv2.cvtColor(self.src, cv2.COLOR_BGR2GRAY) if use_gray else self.src

        template = cv2.imread(
            self.TEMPLATE_PATH + template_path, cv2.IMREAD_GRAYSCALE if use_gray else cv2.IMREAD_COLOR
        )
        w, h = template.shape[1], template.shape[0]

        method = cv2.TM_CCOEFF_NORMED
        res = cv2.matchTemplate(src, template, method)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if show_value:
            print(template_path + " ZNCC value: " + str(max_val))

        top_left = max_loc
        bottom_right = (top_left[0] + w + 1, top_left[1] + h + 1)
        tag = str(time.perf_counter()) + str(random.random())
        if max_val >= threshold:
            return True
        else:
            return False

    @Slot(numpy.ndarray)
    def callback_receive_img(self, frame):
        self.src = frame

    def screenshot(self):
        try:
            # self.imwrite("./.png", self.src)
            # print("capture succeeded:")
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

    @staticmethod
    def imwrite(filename, img, params=None):
        try:
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
