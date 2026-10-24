"""Dedicated capture thread with a latest-frame slot and reconnect backoff."""

from dataclasses import dataclass
import threading
import time
from typing import Protocol
import cv2
import numpy as np


@dataclass
class CameraFrame:
    color: np.ndarray
    timestamp: float
    sequence: int
    depth: np.ndarray | None = None  # Future aligned depth frame, in meters.
    capture_ms: float = 0.0


class CameraSource(Protocol):
    def start(self): ...
    def stop(self): ...
    def latest(self) -> CameraFrame | None: ...


class CameraManager:
    def __init__(self, config):
        self.config = config
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._latest = None
        self.connected = False
        self.error = None
        self.width, self.height = config.camera_width, config.camera_height

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="camera-capture", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        with self._lock:
            self._latest = None
        self.connected = False
        self.error = None

    def set_resolution(self, width, height):
        self.width, self.height = width, height

    def latest(self):
        with self._lock:
            # Capture publishes a new array and never mutates it.
            return self._latest

    def _run(self):
        cap = None
        applied = None
        seq = 0
        try:
            while not self._stop.is_set():
                try:
                    if cap is None:
                        cap = cv2.VideoCapture(self.config.camera_index, cv2.CAP_V4L2)
                        if not cap.isOpened():
                            cap.release()
                            cap = None
                            self.connected = False
                            self.error = f"Cannot open /dev/video{self.config.camera_index}; retrying every 2 seconds"
                            self._stop.wait(2)
                            continue
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                        cap.set(cv2.CAP_PROP_FPS, self.config.target_fps)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        applied = None
                    size = self.width, self.height
                    if applied != size:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
                        applied = size
                    capture_started = time.perf_counter()
                    ok, frame = cap.read()
                    if not ok or frame is None or frame.size == 0:
                        self.connected = False
                        self.error = "Camera read failed; reconnecting"
                        with self._lock:
                            self._latest = None
                        cap.release()
                        cap = None
                        self._stop.wait(1)
                        continue
                    if frame.shape[1::-1] != size:
                        frame = cv2.resize(frame, size)
                    if self.config.mirror_camera:
                        frame = cv2.flip(frame, 1)
                    seq += 1
                    with self._lock:
                        self._latest = CameraFrame(
                            frame,
                            time.monotonic(),
                            seq,
                            capture_ms=(time.perf_counter() - capture_started) * 1000,
                        )
                    self.connected, self.error = True, None
                except Exception as exc:
                    self.connected = False
                    self.error = f"Camera error; reconnecting: {exc}"
                    with self._lock:
                        self._latest = None
                    if cap:
                        cap.release()
                    cap = None
                    self._stop.wait(1)
        finally:
            if cap:
                cap.release()
            self.connected = False
