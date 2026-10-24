"""Latest-only JPEG encoder. A slow encoder never waits in the show loop."""

import threading
import time

import cv2


class PreviewEncoder:
    def __init__(self, metrics, interval=0.12):
        self.metrics = metrics
        self.interval = interval
        self.condition = threading.Condition()
        self.pending = None
        self.jpeg = None
        self.stopped = False
        self.thread = None
        self.dropped = 0
        self.error = None

    def start(self):
        self.thread = threading.Thread(
            target=self._run, name="preview-jpeg", daemon=True
        )
        self.thread.start()

    def submit(self, frame):
        # Ownership transfers by reference: the producer must never mutate frame
        # after submission. Runtime publishes a newly composed array each tick.
        with self.condition:
            if self.pending is not None:
                self.dropped += 1
            self.pending = frame
            self.condition.notify()

    def read(self):
        with self.condition:
            return self.jpeg

    def stop(self):
        with self.condition:
            self.stopped = True
            self.pending = None
            self.condition.notify_all()
        if self.thread:
            self.thread.join(2)

    def _run(self):
        next_encode = 0.0
        while True:
            with self.condition:
                while not self.stopped:
                    remaining = next_encode - time.monotonic()
                    if self.pending is not None and remaining <= 0:
                        break
                    self.condition.wait(remaining if remaining > 0 else None)
                if self.stopped:
                    return
                frame, self.pending = self.pending, None
            started = time.perf_counter()
            try:
                thumb = cv2.resize(
                    frame, (640, max(1, round(frame.shape[0] * 640 / frame.shape[1])))
                )
                ok, encoded = cv2.imencode(
                    ".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 75]
                )
                if ok:
                    with self.condition:
                        self.jpeg = encoded.tobytes()
                    self.error = None
            except Exception as exc:
                self.error = str(exc)
            self.metrics.record("preview_encode", time.perf_counter() - started)
            next_encode = time.monotonic() + self.interval
