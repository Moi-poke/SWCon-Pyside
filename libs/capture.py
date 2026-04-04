from __future__ import annotations

import logging
import os
import pathlib
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import QMutex, QMutexLocker, QObject, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from libs.frame_store import FrameStore


@dataclass
class RectOverlay:
    x: int
    y: int
    w: int
    h: int
    color: QColor
    frames_left: int


class CaptureWorker(QObject):
    image_ready = Signal(QImage)
    frame_ready = Signal(object)
    log = Signal(str, int)

    # compatibility aliases
    change_pixmap_signal = Signal(object, object)
    print_strings = Signal(str, int)
    send_img = Signal(object)

    def __init__(
        self,
        parent: Optional[QObject] = None,
        fps: int = 60,
        camera_id: int = 0,
        frame_store: Optional[FrameStore] = None,
    ) -> None:
        super().__init__(parent)

        self.height: int = 720
        self.width: int = 1280
        self._capture_count = 0
        self.fps: int = max(int(fps), 1)
        self.camera_id: int = int(camera_id)

        self._camera: Optional[cv2.VideoCapture] = None
        self._running: bool = False
        self._timer: Optional[QTimer] = None
        self._latest_frame: Optional[np.ndarray] = None

        self._frame_lock = QMutex()
        self._rect_lock = QMutex()
        self._rect_list: list[RectOverlay] = []

        self._frame_stream_enabled: bool = False
        self._frame_store = frame_store

    @Slot()
    def run(self) -> None:
        """Compatibility entry point."""
        self.start_capture()

    @Slot()
    def start_capture(self) -> None:
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._timer.timeout.connect(self._capture_once)

        if not self._open_camera_impl(self.camera_id):
            self._running = False
            return

        self._running = True
        self._timer.setInterval(max(1, int(round(1000 / max(self.fps, 1)))))
        self._timer.start()
        self.info(f"Capture started. camera_id={self.camera_id}, fps={self.fps}")

    @Slot()
    def stop_capture(self) -> None:
        self._running = False
        if self._timer is not None:
            self._timer.stop()
        self._release_camera()
        self.info("Capture stopped.")

    def stop(self) -> None:
        self.stop_capture()

    def wait(self) -> None:
        return None

    @Slot()
    def _capture_once(self) -> None:
        if not self._running:
            return

        camera = self._camera
        if camera is None or not camera.isOpened():
            self.warning("Camera is not opened.")
            return

        ok, frame = camera.read()
        if not ok or frame is None:
            self.warning("Failed to read frame from camera.")
            return

        latest = frame.copy()
        self._set_latest_frame(latest)

        try:
            qimage = self._build_display_image(latest)
        except RuntimeError:
            self.warning("QImage generation aborted due to RuntimeError.")
            return
        except Exception as exc:
            self.error(f"Image generation failed: {exc}")
            return

        if self._frame_store is not None:
            self._frame_store.set_preview(qimage)
            if self._frame_stream_enabled:
                self._frame_store.set_raw(latest)

    @Slot(int)
    def reopen_camera(self, camera_id: int) -> None:
        self.info(f"Reopen camera requested. new_camera_id={camera_id}")
        self.camera_id = int(camera_id)
        self._release_camera()
        self._open_camera_impl(self.camera_id)

    def open_camera(self, camera_id: int) -> bool:
        self.camera_id = int(camera_id)
        return self._open_camera_impl(self.camera_id)

    def _open_camera_impl(self, camera_id: int) -> bool:
        if self._camera is not None and self._camera.isOpened():
            self.debug("Camera is already opened. Releasing before reopen.")
            self._release_camera()

        if os.name == "nt":
            self.debug("Opening camera via CAP_DSHOW.")
            camera = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        else:
            self.debug("Opening camera via default backend.")
            camera = cv2.VideoCapture(camera_id)

        if not camera.isOpened():
            self.error(f"Camera ID {camera_id} cannot open.")
            try:
                camera.release()
            except Exception:
                pass
            self._camera = None
            return False

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        self._camera = camera
        self.camera_id = int(camera_id)
        self.debug(f"Camera ID {camera_id} opened successfully.")
        return True

    @Slot(int)
    def set_fps(self, fps: int) -> None:
        self.fps = max(int(fps), 1)
        if self._timer is not None:
            self._timer.setInterval(max(1, int(round(1000 / self.fps))))
        self.debug(f"Capture FPS set to {self.fps}")

    def _set_latest_frame(self, frame: np.ndarray) -> None:
        with QMutexLocker(self._frame_lock):
            self._latest_frame = frame.copy()

    def latest_frame_copy(self) -> Optional[np.ndarray]:
        with QMutexLocker(self._frame_lock):
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    @Slot(tuple, tuple, object, int)
    def add_rect(self, t1: tuple, t2: tuple, color: object, frames: int = 120) -> None:
        if not isinstance(color, QColor):
            color = QColor(color)

        overlay = RectOverlay(
            x=int(t1[0]),
            y=int(t1[1]),
            w=int(t2[0]),
            h=int(t2[1]),
            color=color,
            frames_left=max(int(frames), 0),
        )
        with QMutexLocker(self._rect_lock):
            self._rect_list.append(overlay)

    def _consume_rects_for_draw(self) -> list[RectOverlay]:
        with QMutexLocker(self._rect_lock):
            alive: list[RectOverlay] = []
            draw_items: list[RectOverlay] = []

            for item in self._rect_list:
                if item.frames_left <= 0:
                    continue

                draw_items.append(
                    RectOverlay(
                        x=item.x,
                        y=item.y,
                        w=item.w,
                        h=item.h,
                        color=item.color,
                        frames_left=item.frames_left,
                    )
                )

                item.frames_left -= 1
                if item.frames_left > 0:
                    alive.append(item)

            self._rect_list = alive

        return draw_items

    def _build_display_image(self, frame_bgr: np.ndarray) -> QImage:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        image = QImage(
            rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        ).copy()

        rects = self._consume_rects_for_draw()
        if rects:
            painter = QPainter(image)
            try:
                pen = QPen()
                pen.setWidth(2)
                for rect in rects:
                    pen.setColor(rect.color)
                    painter.setPen(pen)
                    painter.drawRect(rect.x, rect.y, rect.w, rect.h)
            finally:
                painter.end()

        return image

    @Slot(bool)
    def set_frame_stream_enabled(self, enabled: bool) -> None:
        self._frame_stream_enabled = bool(enabled)

    @Slot(object, object, object, object, str)
    def save_capture(
        self,
        filename: object = None,
        crop: object = None,
        crop_ax: object = None,
        img: object = None,
        capture_dir: str = "./ScreenShot",
    ) -> None:
        if crop_ax is None:
            crop_ax = [0, 0, 1280, 720]

        dt_now = datetime.now()
        if filename is None or filename == "":
            out_name = dt_now.strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        else:
            out_name = f"{filename}.png"

        if isinstance(img, np.ndarray):
            image = img.copy()
        else:
            image = self.latest_frame_copy()

        if image is None:
            self.error("No frame available to save.")
            return

        if crop in (1, "1"):
            image = image[crop_ax[1] : crop_ax[3], crop_ax[0] : crop_ax[2]]
        elif crop in (2, "2"):
            image = image[
                crop_ax[1] : crop_ax[1] + crop_ax[3],
                crop_ax[0] : crop_ax[0] + crop_ax[2],
            ]

        capture_path = pathlib.Path(capture_dir)
        capture_path.mkdir(parents=True, exist_ok=True)

        save_path = capture_path / out_name
        ret = self.imwrite(save_path, image)

        if ret:
            self.debug(f"Capture succeeded: {save_path}")
        else:
            self.error("Capture failed.")

    def saveCapture(
        self,
        filename: object = None,
        crop: object = None,
        crop_ax: object = None,
        img: object = None,
        capture_dir: str = "./ScreenShot",
    ) -> None:
        self.save_capture(
            filename=filename,
            crop=crop,
            crop_ax=crop_ax,
            img=img,
            capture_dir=capture_dir,
        )

    def imwrite(
        self,
        filename: str | pathlib.Path,
        img: np.ndarray,
        params: Optional[list[int]] = None,
    ) -> bool:
        try:
            target = pathlib.Path(filename)
            ext = target.suffix or ".png"
            result, encoded = cv2.imencode(ext, img, params)
            if not result:
                return False
            with open(target, "wb") as f:
                encoded.tofile(f)
            return True
        except Exception as exc:
            self.error(f"Image write error: {exc}")
            return False

    @Slot(bool)
    def callback_return_img(self, bl: bool) -> None:
        if not bl:
            return
        frame = self.latest_frame_copy()
        if frame is not None:
            self.send_img.emit(frame.copy())

    def destroy(self) -> None:
        self._release_camera()

    def _release_camera(self) -> None:
        camera = self._camera
        self._camera = None
        if camera is not None:
            try:
                if camera.isOpened():
                    camera.release()
                    self.debug("Camera destroyed")
            except Exception as exc:
                self.warning(f"Camera release raised exception: {exc}")

    def _emit_log(self, level: int, message: str) -> None:
        msg = f"thread id={threading.get_ident()} {message}"
        self.log.emit(msg, level)
        self.print_strings.emit(msg, level)

    def debug(self, s: str) -> None:
        self._emit_log(logging.DEBUG, s)

    def info(self, s: str) -> None:
        self._emit_log(logging.INFO, s)

    def warning(self, s: str) -> None:
        self._emit_log(logging.WARNING, s)

    def error(self, s: str) -> None:
        self._emit_log(logging.ERROR, s)

    def critical(self, s: str) -> None:
        self._emit_log(logging.CRITICAL, s)
