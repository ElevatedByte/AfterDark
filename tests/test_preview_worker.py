import threading
import time

import cv2
import numpy as np

from app.renderer.metrics import StageMetrics
from app.renderer.preview import PreviewEncoder


def test_slow_encoder_keeps_only_newest_frame_without_blocking_producer(monkeypatch):
    started, release = threading.Event(), threading.Event()
    encoded_values = []

    def encode(extension, frame, options):
        started.set()
        release.wait(2)
        encoded_values.append(int(frame[0, 0, 0]))
        return True, np.array([encoded_values[-1]], np.uint8)

    monkeypatch.setattr(cv2, "imencode", encode)
    worker = PreviewEncoder(StageMetrics(), interval=0)
    worker.start()
    try:
        worker.submit(np.zeros((8, 8, 3), np.uint8))
        assert started.wait(1)
        before = time.monotonic()
        for value in range(1, 20):
            worker.submit(np.full((8, 8, 3), value, np.uint8))
        assert time.monotonic() - before < 0.5
        assert worker.dropped == 18
        release.set()
        deadline = time.monotonic() + 2
        while worker.read() != bytes([19]) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert encoded_values == [0, 19]
    finally:
        release.set()
        worker.stop()
    assert not worker.thread.is_alive()


def test_timing_samples_are_bounded():
    metrics = StageMetrics(capacity=3)
    for value in range(10):
        metrics.record("composition", value / 1000)
    assert metrics.snapshot()["composition"] == {
        "samples": 3,
        "median_ms": 8,
        "p95_ms": 8.9,
    }
