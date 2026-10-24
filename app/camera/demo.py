"""Explicit rehearsal source, never presented as real camera/model output."""

import math
import time
import cv2
import numpy as np
from app.camera.camera_manager import CameraFrame
from app.tracking.models import PersonTrackingData, Point


class DemoCamera:
    def __init__(self, config):
        self.width, self.height = config.camera_width, config.camera_height
        self.connected = False
        self.error = None
        self.seq = 0
        self.start_time = time.monotonic()
        self.people = []

    def start(self):
        self.connected = True

    def stop(self):
        self.connected = False

    def set_resolution(self, w, h):
        self.width, self.height = w, h

    def latest(self):
        if not self.connected:
            return None
        now = time.monotonic()
        t = now - self.start_time
        h, w = self.height, self.width
        frame = np.zeros((h, w, 3), np.uint8)
        frame[:] = (33, 23, 29)
        for y in range(int(h * 0.77), h, 30):
            cv2.line(frame, (0, y), (w, y), (58, 40, 47), 1)
        for x in range(-w, w * 2, 100):
            cv2.line(frame, (w // 2, int(h * 0.75)), (x, h), (58, 40, 47), 1)
        cv2.circle(
            frame,
            (int(w * 0.87), int(h * 0.16)),
            int(h * 0.065),
            (85, 132, 169),
            -1,
            cv2.LINE_AA,
        )
        people = []
        for i, cx in enumerate((0.30, 0.67)):
            phase = t * 1.6 + i * 2
            bounce = 0.015 * math.sin(phase * 2)
            sway = 0.025 * math.sin(phase)
            cx += sway
            coords = {
                "head": (cx, 0.26 + bounce),
                "left_shoulder": (cx - 0.052, 0.37 + bounce),
                "right_shoulder": (cx + 0.052, 0.37 + bounce),
                "left_elbow": (cx - 0.09, 0.44 + 0.08 * math.sin(phase)),
                "right_elbow": (cx + 0.09, 0.42 + 0.08 * math.cos(phase)),
                "left_hand": (
                    cx - 0.15 + 0.05 * math.cos(phase * 2),
                    0.31 + 0.16 * math.sin(phase),
                ),
                "right_hand": (
                    cx + 0.15 + 0.05 * math.sin(phase * 2),
                    0.30 + 0.16 * math.cos(phase),
                ),
                "left_hip": (cx - 0.035, 0.59 + bounce),
                "right_hip": (cx + 0.035, 0.59 + bounce),
                "left_knee": (cx - 0.055, 0.73 + bounce),
                "right_knee": (cx + 0.045, 0.73 - bounce),
                "left_ankle": (cx - 0.08, 0.89),
                "right_ankle": (cx + 0.07, 0.89),
                "left_foot": (cx - 0.105, 0.91),
                "right_foot": (cx + 0.095, 0.91),
            }
            points = {k: Point(*v) for k, v in coords.items()}
            mask = np.zeros((h, w), np.float32)

            def line(a, b, thick):
                cv2.line(
                    mask,
                    points[a].pixel(frame),
                    points[b].pixel(frame),
                    1.0,
                    thick,
                    cv2.LINE_AA,
                )

            cv2.ellipse(
                mask,
                points["head"].pixel(frame),
                (int(w * 0.028), int(h * 0.045)),
                0,
                0,
                360,
                1.0,
                -1,
            )
            poly = np.array(
                [
                    points[k].pixel(frame)
                    for k in (
                        "left_shoulder",
                        "right_shoulder",
                        "right_hip",
                        "left_hip",
                    )
                ]
            )
            cv2.fillPoly(mask, [poly], 1.0)
            for a, b in [
                ("left_shoulder", "left_elbow"),
                ("left_elbow", "left_hand"),
                ("right_shoulder", "right_elbow"),
                ("right_elbow", "right_hand"),
                ("left_hip", "left_knee"),
                ("left_knee", "left_ankle"),
                ("right_hip", "right_knee"),
                ("right_knee", "right_ankle"),
            ]:
                line(a, b, max(6, w // 65))
            color = np.array((96, 110, 141) if i == 0 else (111, 112, 77))
            frame = (frame * (1 - mask[:, :, None]) + color * mask[:, :, None]).astype(
                np.uint8
            )
            people.append(
                PersonTrackingData(
                    -1, points, (cx - 0.21, 0.14, cx + 0.21, 0.92), 1.0, mask
                )
            )
        cv2.putText(
            frame,
            "REHEARSAL / SYNTHETIC DANCERS",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (138, 155, 181),
            1,
            cv2.LINE_AA,
        )
        self.people = people
        self.seq += 1
        return CameraFrame(frame, now, self.seq)
