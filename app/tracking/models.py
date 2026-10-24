"""Sensor-independent image-space data. x/y are normalized; depth is optional meters."""

from dataclasses import dataclass, field
from math import hypot, isfinite
from typing import Protocol
import numpy as np

LANDMARK_INDEX = {
    "head": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_hand": 15,
    "right_hand": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_foot": 31,
    "right_foot": 32,
}
BONES = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_hand"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_hand"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"),
    ("right_knee", "right_ankle"),
    ("left_ankle", "left_foot"),
    ("right_ankle", "right_foot"),
]


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    confidence: float = 1.0
    depth_m: float | None = None

    def distance(self, other):
        return hypot(self.x - other.x, self.y - other.y)

    def pixel(self, frame):
        h, w = frame.shape[:2]
        return round(self.x * (w - 1)), round(self.y * (h - 1))


@dataclass
class PersonTrackingData:
    id: int
    landmarks: dict[str, Point]
    bounding_box: tuple[float, float, float, float]
    confidence: float
    segmentation_mask: np.ndarray | None = field(default=None, repr=False)

    def point(self, name, threshold=0.35):
        p = self.landmarks.get(name)
        return p if p and p.confidence >= threshold else None

    @property
    def head(self):
        return self.point("head")

    @property
    def left_hand(self):
        return self.point("left_hand")

    @property
    def right_hand(self):
        return self.point("right_hand")

    @property
    def shoulders(self):
        return self.point("left_shoulder"), self.point("right_shoulder")

    @property
    def hips(self):
        return self.point("left_hip"), self.point("right_hip")

    @property
    def knees(self):
        return self.point("left_knee"), self.point("right_knee")

    @property
    def feet(self):
        return self.point("left_foot"), self.point("right_foot")

    @property
    def center(self):
        a, b = self.hips
        if a and b:
            return Point((a.x + b.x) / 2, (a.y + b.y) / 2)
        x1, y1, x2, y2 = self.bounding_box
        return Point((x1 + x2) / 2, (y1 + y2) / 2)


class PoseTracker(Protocol):
    def detect(
        self, bgr: np.ndarray, timestamp_ms: int
    ) -> list[PersonTrackingData]: ...
    def close(self) -> None: ...


def map_landmarks(landmarks, mask=None):
    points = {}
    for name, i in LANDMARK_INDEX.items():
        if i >= len(landmarks):
            continue
        lm = landmarks[i]
        values = [
            lm.x,
            lm.y,
            getattr(lm, "visibility", 1.0),
            getattr(lm, "presence", 1.0),
        ]
        if any(v is None or not isfinite(v) for v in values):
            continue
        x, y, visibility, presence = values
        # Out-of-frame coordinates stay bounded but are not usable for gestures.
        conf = min(visibility, presence) if 0 <= x <= 1 and 0 <= y <= 1 else 0
        points[name] = Point(
            max(0.0, min(1.0, x)), max(0.0, min(1.0, y)), max(0.0, min(1.0, conf))
        )
    visible = [p for p in points.values() if p.confidence >= 0.35]
    if not visible:
        return None
    bbox = (
        min(p.x for p in visible),
        min(p.y for p in visible),
        max(p.x for p in visible),
        max(p.y for p in visible),
    )
    return PersonTrackingData(
        -1, points, bbox, sum(p.confidence for p in visible) / len(visible), mask
    )
