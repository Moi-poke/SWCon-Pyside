"""CameraProcess — カメラキャプチャを子プロセスで実行する.

カメラオープンをプロセス分離することで、DirectShow の
同一プロセス内マルチカメラ問題を回避する。

アーキテクチャ:
    CameraProcess (メインプロセス側)
        ├── multiprocessing.Process  (_camera_capture_loop)
        ├── shared_memory            (フレーム転送用)
        ├── Lock                     (読み書き排他)
        ├── Event                    (停止シグナル)
        └── Value('i')              (動的FPS変更)

共有メモリレイアウト:
    [0:8]   uint64  シーケンス番号 (リトルエンディアン)
    [8:]    bytes   BGR フレームデータ (H * W * 3)
"""
from __future__ import annotations

import logging
import multiprocessing
import os
import struct
import time
from multiprocessing import Event, Lock, Process, Value
from multiprocessing.shared_memory import SharedMemory
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# 共有メモリ先頭の seq カウンタサイズ
_SEQ_SIZE = 8
_SEQ_STRUCT = struct.Struct("<Q")  # uint64 リトルエンディアン


# ======================================================================
# 子プロセスのメインループ (モジュールレベル関数 — pickle 可能)
# ======================================================================


def _camera_capture_loop(
    shm_name: str,
    frame_size: int,
    width: int,
    height: int,
    camera_id: int,
    fps_value: "multiprocessing.Value",
    stop_event: "multiprocessing.Event",
    lock: "multiprocessing.Lock",
) -> None:
    """子プロセスで実行されるカメラキャプチャループ.

    Parameters
    ----------
    shm_name : str
        共有メモリの名前
    frame_size : int
        1フレームのバイト数 (H * W * 3)
    width, height : int
        カメラ解像度
    camera_id : int
        カメラデバイスID
    fps_value : Value('i')
        FPS (メインプロセスから動的に変更可能)
    stop_event : Event
        停止シグナル
    lock : Lock
        共有メモリの読み書き排他
    """
    shm: Optional[SharedMemory] = None
    camera: Optional[cv2.VideoCapture] = None

    try:
        # ---- 共有メモリにアタッチ ----
        shm = SharedMemory(name=shm_name, create=False)

        # ---- カメラオープン ----
        if os.name == "nt":
            camera = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        else:
            camera = cv2.VideoCapture(camera_id)

        if not camera.isOpened():
            # オープン失敗 → seq=0 のまま終了
            return

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        seq: int = 0

        while not stop_event.is_set():
            fps = max(int(fps_value.value), 1)
            interval = 1.0 / fps

            t0 = time.monotonic()

            ok, frame = camera.read()
            if not ok or frame is None:
                # フレーム読み取り失敗 → 少し待ってリトライ
                time.sleep(0.05)
                continue

            # フレームサイズの補正 (カメラが異なる解像度を返す場合)
            if frame.shape[0] != height or frame.shape[1] != width:
                frame = cv2.resize(frame, (width, height))

            raw = frame.tobytes()

            # フレームサイズ検証
            if len(raw) != frame_size:
                continue

            seq += 1
            seq_bytes = _SEQ_STRUCT.pack(seq)

            # ---- 共有メモリに書き込み ----
            with lock:
                shm.buf[0:_SEQ_SIZE] = seq_bytes
                shm.buf[_SEQ_SIZE : _SEQ_SIZE + frame_size] = raw

            # ---- FPS 制御 ----
            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception:
        # 子プロセスの例外は握りつぶす (メイン側が stop_event で監視)
        pass
    finally:
        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass
        if shm is not None:
            try:
                shm.close()
            except Exception:
                pass


# ======================================================================
# メインプロセス側のラッパークラス
# ======================================================================


class CameraProcess:
    """カメラキャプチャ子プロセスの管理クラス.

    Usage::

        cam = CameraProcess(camera_id=0, width=1280, height=720, fps=60)
        if cam.start():
            frame = cam.read_frame()    # np.ndarray or None
            cam.set_fps(30)
            cam.stop()
    """

    def __init__(
        self,
        camera_id: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 60,
    ) -> None:
        self._camera_id = camera_id
        self._width = width
        self._height = height
        self._frame_size = width * height * 3  # BGR

        self._fps_value: Value = Value("i", max(fps, 1))
        self._stop_event: Event = Event()
        self._lock: Lock = Lock()

        self._shm: Optional[SharedMemory] = None
        self._process: Optional[Process] = None
        self._last_seq: int = 0

    @property
    def camera_id(self) -> int:
        return self._camera_id

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def start(self) -> bool:
        """子プロセスを起動してカメラキャプチャを開始する."""
        if self.is_running:
            self.stop()

        try:
            shm_size = _SEQ_SIZE + self._frame_size
            self._shm = SharedMemory(create=True, size=shm_size)

            # seq=0 に初期化
            self._shm.buf[0:_SEQ_SIZE] = _SEQ_STRUCT.pack(0)
            self._last_seq = 0

            self._stop_event.clear()

            self._process = Process(
                target=_camera_capture_loop,
                args=(
                    self._shm.name,
                    self._frame_size,
                    self._width,
                    self._height,
                    self._camera_id,
                    self._fps_value,
                    self._stop_event,
                    self._lock,
                ),
                daemon=True,
            )
            self._process.start()
            logger.info(
                "CameraProcess started: camera_id=%d, pid=%d, shm=%s",
                self._camera_id,
                self._process.pid or -1,
                self._shm.name,
            )
            return True

        except Exception as exc:
            logger.error("CameraProcess start failed: %s", exc)
            self._cleanup_shm()
            return False

    def stop(self, timeout: float = 3.0) -> None:
        """子プロセスを停止する."""
        self._stop_event.set()

        if self._process is not None:
            self._process.join(timeout=timeout)
            if self._process.is_alive():
                logger.warning(
                    "CameraProcess pid=%d did not exit in %.1fs, terminating",
                    self._process.pid or -1,
                    timeout,
                )
                self._process.terminate()
                self._process.join(timeout=1.0)
            self._process = None

        self._cleanup_shm()
        logger.info("CameraProcess stopped: camera_id=%d", self._camera_id)

    def read_frame(self) -> Optional[np.ndarray]:
        """共有メモリから最新フレームを読み取る.

        新しいフレームがなければ None を返す。
        """
        if self._shm is None:
            return None

        with self._lock:
            seq_bytes = bytes(self._shm.buf[0:_SEQ_SIZE])
            seq = _SEQ_STRUCT.unpack(seq_bytes)[0]

            if seq == 0 or seq == self._last_seq:
                return None

            raw = bytes(self._shm.buf[_SEQ_SIZE : _SEQ_SIZE + self._frame_size])
            self._last_seq = seq

        frame = np.frombuffer(raw, dtype=np.uint8).reshape(
            (self._height, self._width, 3)
        )
        return frame

    def set_fps(self, fps: int) -> None:
        """FPS を動的に変更する."""
        self._fps_value.value = max(int(fps), 1)

    def _cleanup_shm(self) -> None:
        if self._shm is not None:
            try:
                self._shm.close()
                self._shm.unlink()
            except Exception:
                pass
            self._shm = None

    def __del__(self) -> None:
        try:
            self.stop(timeout=1.0)
        except Exception:
            pass
