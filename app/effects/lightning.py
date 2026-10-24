import random
import cv2
import numpy as np
from app.effects.base import Effect


class Lightning(Effect):
    name = "lightning"

    def initialize(self):
        self.remaining = 0.0
        self.bolts = []
        self.branches = []
        self.rng = random.Random()

    def reset(self):
        super().reset()
        self.remaining = 0.0
        self.bolts = []
        self.branches = []

    @property
    def alive(self):
        return self.remaining > 0

    def trigger(self, people=None):
        self.remaining = 0.28
        x = self.rng.uniform(0.2, 0.8)
        self.bolts = [(x, 0)]
        for i in range(1, 11):
            self.bolts.append(
                (max(0.05, min(0.95, x + self.rng.uniform(-0.12, 0.12))), i / 10)
            )

        self.branches = []
        for index in (3, 5, 7):
            sx, sy = self.bolts[index]
            direction = self.rng.choice((-1, 1))
            self.branches.append(
                [(sx, sy)]
                + [
                    (
                        max(
                            0,
                            min(
                                1,
                                sx
                                + direction * step * 0.055
                                + self.rng.uniform(-0.02, 0.02),
                            ),
                        ),
                        min(1, sy + step * 0.035),
                    )
                    for step in range(1, 5)
                ]
            )

    def update(self, frame, tracking_data, delta_time):
        super().update(frame, tracking_data, delta_time)
        self.remaining = max(0, self.remaining - delta_time)

    def render(self, frame):
        if self.remaining <= 0:
            return frame
        intensity = self.settings.get("effect_intensity", 0.75) * self.remaining / 0.28
        if intensity <= 0:
            return frame
        flash = np.full_like(frame, (255, 247, 236))
        frame = cv2.addWeighted(frame, 1 - intensity * 0.55, flash, intensity * 0.55, 0)
        layer = frame.copy()
        scale = max(0.5, frame.shape[1] / 1920)
        for path, width in [
            (self.bolts, 1.0),
            *[(branch, 0.5) for branch in self.branches],
        ]:
            pts = np.array(
                [
                    (round(x * frame.shape[1]), round(y * frame.shape[0]))
                    for x, y in path
                ],
                np.int32,
            )
            for color, stroke in (
                ((108, 56, 63), 28),
                ((212, 139, 167), 15),
                ((255, 220, 245), 7),
                ((255, 255, 255), 3),
            ):
                cv2.polylines(
                    layer,
                    [pts],
                    False,
                    color,
                    max(1, round(stroke * scale * width)),
                    cv2.LINE_AA,
                )
        return cv2.addWeighted(
            layer, min(1, intensity * 2), frame, 1 - min(1, intensity * 2), 0
        )
