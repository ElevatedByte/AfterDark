"""Smoothed, face-anchored sprites shared by the Halloween head characters."""

from abc import abstractmethod
import math

import cv2
import numpy as np

from app.effects.base import Effect


def overlay(frame, sprite, cx, cy, alpha=1.0):
    h, w = sprite.shape[:2]
    fh, fw = frame.shape[:2]
    x, y = round(cx - w / 2), round(cy - h / 2)
    x1, y1, x2, y2 = max(0, x), max(0, y), min(fw, x + w), min(fh, y + h)
    if x1 >= x2 or y1 >= y2:
        return
    roi = sprite[y1 - y : y2 - y, x1 - x : x2 - x]
    a = (roi[:, :, 3:4].astype(np.float32) / 255) * alpha
    frame[y1:y2, x1:x2] = (frame[y1:y2, x1:x2] * (1 - a) + roi[:, :, :3] * a).astype(
        np.uint8
    )


class HeadOverlay(Effect):
    # Position of the tracked nose within the artwork, as fractions of its size.
    # Tall hats and collars need a face anchor, not the center of the sprite.
    anchor = (0.5, 0.5)
    shoulder_scale = 1.08

    @abstractmethod
    def create_asset(self):
        """Return an original BGRA sprite; called once when the effect is created."""

    def initialize(self):
        self.asset = self.create_asset()
        self.poses = {}

    def reset(self):
        super().reset()
        self.poses = {}

    def update(self, frame, tracking_data, delta_time):
        super().update(frame, tracking_data, delta_time)
        h, w = frame.shape[:2]
        poses = {}
        retention = 0.35 ** (max(0, delta_time) * 30)
        for person in tracking_data:
            a, b = person.shoulders
            if not person.head or not a or not b:
                continue
            dx, dy = (b.x - a.x) * w, (b.y - a.y) * h
            angle = (math.degrees(math.atan2(dy, dx)) + 90) % 180 - 90
            target = np.array(
                [
                    person.head.x,
                    person.head.y,
                    math.hypot(dx, dy) / w,
                    max(-25, min(25, angle)),
                ]
            )
            previous = self.poses.get(person.id)
            poses[person.id] = (
                target
                if previous is None
                else previous * retention + target * (1 - retention)
            )
        self.poses = poses

    def render(self, frame):
        intensity = self.settings.get("effect_intensity", 0.75)
        if intensity <= 0:
            return frame
        fh, fw = frame.shape[:2]
        ah, aw = self.asset.shape[:2]
        anchor = (self.anchor[0] * aw, self.anchor[1] * ah)
        if hasattr(frame, "sprite"):
            for x, y, width, angle in self.poses.values():
                size = max(24, min(width * fw * self.shoulder_scale, fw / 2))
                frame.sprite(
                    self.asset,
                    x * fw,
                    y * fh,
                    size,
                    size * ah / aw,
                    angle=-angle,
                    alpha=intensity,
                    anchor=self.anchor,
                )
            return frame
        corners = np.array([[0, 0, 1], [aw, 0, 1], [0, ah, 1], [aw, ah, 1]])
        for x, y, width, angle in self.poses.values():
            size = max(24, min(width * fw * self.shoulder_scale, fw / 2))
            matrix = cv2.getRotationMatrix2D(anchor, -angle, size / aw)
            bounds = corners @ matrix.T
            origin = np.floor(bounds.min(axis=0))
            sw, sh = (np.ceil(bounds.max(axis=0)) - origin).astype(int)
            matrix[:, 2] -= origin
            # Expand the rotated canvas so hat tips, ears and bolts aren't cut off.
            sprite = cv2.warpAffine(self.asset, matrix, (int(sw), int(sh)))
            pivot = matrix @ np.array([*anchor, 1])
            overlay(
                frame,
                sprite,
                x * fw + sw / 2 - pivot[0],
                y * fh + sh / 2 - pivot[1],
                intensity,
            )
        return frame
