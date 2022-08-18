import logging
import os
import threading
import time
from datetime import datetime
from multiprocessing import Array, Process, shared_memory

import cv2
import numpy
import numpy as np
from PySide6.QtCore import QObject, QSize, Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage


class CaptureWorker(QObject):
    change_pixmap_signal = Signal(QImage)
    print_strings = Signal(str, type(logging.DEBUG))
    send_img = Signal(numpy.ndarray)
    playing = True

    def __init__(self, parent=None, fps=60, camera_id=0):
        super().__init__(parent)
        self.height = 720
        self.width = 1280
        self.fps = 60
        self.camera = None
        self.trained_file = None
        self.status = True
        self.cap = True
        self.frame = None
        self.camera_id = camera_id
        # self.a = np.zeros((720, 1280, 3))
        # self.shm = shared_memory.SharedMemory(create=True, size=self.a.nbytes, name='cam')  # 共有メモリを作成
        # self.mp_frame = np.ndarray(self.a.shape, dtype=self.a.dtype, buffer=self.shm.buf)
        # self.p = Process(target=cam(self.camera_id))

    def run(self):
        # self.p.start()
        self.open_camera(self.camera_id)
        while self.playing:
            if self.camera is not None:
                start = time.perf_counter()
                ret, self.frame = self.camera.read()
                if ret:
                    # self.image_rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = self.frame.shape
                    bytes_per_line = ch * w
                    image = QImage(self.frame, w, h, bytes_per_line, QImage.Format.Format_BGR888)
                    self.change_pixmap_signal.emit(image)
                # h, w, ch = self.mp_frame.shape
                # bytes_per_line = ch * w
                # image = QImage(self.mp_frame, w, h, bytes_per_line, QImage.Format.Format_BGR888)
                # self.change_pixmap_signal.emit(image)
                time.sleep(max(1 / self.fps - (time.perf_counter() - start), 0))
        self.destroy()

    def open_camera(self, camera_id):
        # self.p.kill()
        # self.p = Process(target=cam(camera_id))
        # self.p.start()
        if self.camera is not None and self.camera.isOpened():
            self.debug("Camera is already opened")
            self.destroy()

        if self.camera is None or self.camera_id != camera_id:
            if os.name == "nt":
                self.debug("NT OS")
                self.camera = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            # self.camera = cv2.VideoCapture(cameraId)
            else:
                self.debug("Not NT OS")
                self.camera = cv2.VideoCapture(camera_id)

            if not self.camera.isOpened():
                self.error(f"Camera ID {camera_id} cannot open.")
                return
            self.debug(f"Camera ID {camera_id} opened successfully.")
            # print(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            # self.camera.set(cv2.CAP_PROP_FPS, 60)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera_id = camera_id
        else:
            self.debug("Same Camera ID")

    def saveCapture(self, filename=None, crop=None, crop_ax=None, img=None, capture_dir="./ScreenShot"):
        if crop_ax is None:
            crop_ax = [0, 0, 1280, 720]
        else:
            pass
            # print(crop_ax)

        dt_now = datetime.now()
        if filename is None or filename == "":
            filename = dt_now.strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        else:
            filename = filename + ".png"

        if crop is None:
            image = self.frame
        elif crop is 1 or crop is "1":
            image = self.frame[crop_ax[1] : crop_ax[3], crop_ax[0] : crop_ax[2]]
        elif crop is 2 or crop is "2":
            image = self.frame[crop_ax[1] : crop_ax[1] + crop_ax[3], crop_ax[0] : crop_ax[0] + crop_ax[2]]
        elif img is not None:
            image = img
        else:
            image = self.frame

        if not os.path.exists(capture_dir):
            os.makedirs(capture_dir)
            self.debug("Created Capture folder")

        save_path = os.path.join(capture_dir, filename)

        ret = self.imwrite(save_path, image)
        if ret:
            self.debug(f"Capture succeeded: {save_path}")
        else:
            self.error(f"Capture Failed.")

    def imwrite(self, filename, img, params=None):
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
            self.error(f"Image Write Error: {e}")
        return False

    def set_fps(self, fps):
        self.fps = int(fps)

    def stop(self):
        self.playing = False
        self.wait()

    def destroy(self):
        if self.camera is not None and self.camera.isOpened():
            self.camera.release()
            self.camera = None
            self.debug("Camera destroyed")

    @Slot(bool)
    def callback_return_img(self, bl: bool):
        print("RECEIVE SIGNAL")
        if bl:
            print("SEND IMG")
            self.send_img.emit(self.frame)

    # ログをメインに飛ばすため
    def debug(self, s):
        s = f"thread id={threading.get_ident()} " + s
        self.print_strings.emit(s, logging.DEBUG)

    def info(self, s):
        s = f"thread id={threading.get_ident()} " + s
        self.print_strings.emit(s, logging.INFO)

    def warning(self, s):
        s = f"thread id={threading.get_ident()} " + s
        self.print_strings.emit(s, logging.WARNING)

    def error(self, s):
        s = f"thread id={threading.get_ident()} " + s
        self.print_strings.emit(s, logging.ERROR)

    def critical(self, s):
        s = f"thread id={threading.get_ident()} " + s
        self.print_strings.emit(s, logging.CRITICAL)

    def wait(self):
        pass
