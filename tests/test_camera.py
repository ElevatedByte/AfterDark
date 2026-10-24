import threading
import time
import numpy as np
from app.camera.camera_manager import CameraManager
from app.config import Config


def test_reconnects_after_read_failure_and_releases_capture(monkeypatch):
    captures = []

    class FakeCapture:
        def __init__(self, *args):
            self.reads = 0
            self.released = False
            captures.append(self)

        def isOpened(self):
            return True

        def set(self, *args):
            return True

        def read(self):
            self.reads += 1
            time.sleep(0.001)
            if self is captures[0]:
                return False, None
            return True, np.zeros((240, 320, 3), np.uint8)

        def release(self):
            self.released = True

    class FastEvent(threading.Event):
        def wait(self, timeout=None):
            return super().wait(min(timeout or 0.01, 0.01))

    monkeypatch.setattr("app.camera.camera_manager.cv2.VideoCapture", FakeCapture)
    camera = CameraManager(Config(camera_width=320, camera_height=240))
    camera._stop = FastEvent()
    camera.start()
    try:
        deadline = time.monotonic() + 2
        while camera.latest() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert camera.connected and camera.latest() is not None
        assert len(captures) >= 2 and captures[0].released
    finally:
        camera.stop()
    assert all(cap.released for cap in captures)
    assert camera.latest() is None and not camera.connected


def test_reconnects_when_native_read_raises(monkeypatch):
    captures = []

    class FakeCapture:
        def __init__(self, *args):
            captures.append(self)

        def isOpened(self):
            return True

        def set(self, *args):
            return True

        def read(self):
            time.sleep(0.001)
            if self is captures[0]:
                raise OSError("USB disconnected")
            return True, np.zeros((240, 320, 3), np.uint8)

        def release(self):
            pass

    class FastEvent(threading.Event):
        def wait(self, timeout=None):
            return super().wait(0.01)

    monkeypatch.setattr("app.camera.camera_manager.cv2.VideoCapture", FakeCapture)
    camera = CameraManager(Config(camera_width=320, camera_height=240))
    camera._stop = FastEvent()
    camera.start()
    try:
        deadline = time.monotonic() + 2
        while camera.latest() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert camera.connected and len(captures) >= 2
    finally:
        camera.stop()
    assert camera.error is None
