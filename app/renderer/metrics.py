"""Bounded, thread-safe stage samples. Values are wall-clock milliseconds."""

from collections import defaultdict, deque
from threading import Lock

import numpy as np


class StageMetrics:
    def __init__(self, capacity=300):
        self.capacity = capacity
        self.samples = defaultdict(lambda: deque(maxlen=capacity))
        self.lock = Lock()

    def record(self, stage, seconds):
        with self.lock:
            self.samples[stage].append(max(0.0, seconds * 1000))

    def snapshot(self):
        with self.lock:
            return {
                name: {
                    "samples": len(values),
                    "median_ms": round(float(np.median(values)), 3),
                    "p95_ms": round(float(np.percentile(values, 95)), 3),
                }
                for name, values in self.samples.items()
                if values
            }
