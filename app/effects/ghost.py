from collections import deque
import math
import cv2
import numpy as np
from app.effects.base import Effect
from app.effects.head_overlay import overlay as paste_sprite
from app.renderer.sprites import load_sprite


class Ghost(Effect):
    name = "ghost"

    def initialize(self):
        self.history = deque(maxlen=8)
        self.background = None
        self.appearance = 0.0
        self.sample = 0.0
        self.mask = None
        self._appearance_sprite = None
        self._appearance_size = None

    def reset(self):
        super().reset()
        self.initialize()

    @property
    def alive(self):
        return self.appearance > 0 or bool(self.history)

    def trigger(self, people=None):
        self.appearance = 1.7

    def update(self, frame, tracking_data, delta_time):
        super().update(frame, tracking_data, delta_time)
        self.appearance = max(0, self.appearance - delta_time)
        # Ghost echoes are deliberately soft; bound only their camera-derived buffers.
        # The foreground and apparition sprite remain at full output resolution.
        scale = min(0.5, 480 / frame.shape[1], 270 / frame.shape[0])
        self.small = cv2.resize(
            frame,
            (
                max(1, round(frame.shape[1] * scale)),
                max(1, round(frame.shape[0] * scale)),
            ),
        )
        if self.background is None or self.background.shape != self.small.shape:
            self.background = self.small.astype(np.float32)
            self.history.clear()
        masks = []
        for person in tracking_data:
            if person.segmentation_mask is not None:
                masks.append(
                    cv2.resize(person.segmentation_mask, self.small.shape[1::-1])
                )
        self.mask = (
            np.clip(np.maximum.reduce(masks), 0, 1)
            if masks
            else np.zeros(self.small.shape[:2], np.float32)
        )
        # Update only known background pixels. RGB alone cannot recover unseen background.
        bg_alpha = (1 - self.mask[:, :, None]) * min(1, delta_time * 0.4)
        self.background = self.background * (1 - bg_alpha) + self.small * bg_alpha
        self.sample += delta_time
        strength = self.settings.get("ghost_trail_strength", 0.65)
        self.history = deque(
            [
                (im, m, age + delta_time)
                for im, m, age in self.history
                if age + delta_time < 0.2 + strength * 1.8
            ],
            maxlen=8,
        )
        if self.sample >= 0.10 and masks and strength > 0:
            # Pre-tint once per sample, not eight times per rendered frame.
            tinted = np.minimum(
                255,
                self.small.astype(np.float32) * np.array([1.15, 1.07, 0.82], np.float32)
                + 20,
            )
            self.history.append((tinted, self.mask.copy(), 0.0))
            self.sample = 0

    def render(self, frame):
        intensity = self.settings.get("effect_intensity", 0.75)
        if intensity <= 0:
            return frame
        current = self.small.astype(np.float32)
        alpha = self.mask[:, :, None] * 0.55 * intensity
        current += (self.background - current) * alpha
        strength = self.settings.get("ghost_trail_strength", 0.65)
        for im, mask, age in self.history:
            opacity = (
                strength * 0.32 * math.exp(-age / max(0.06, strength * 0.6)) * intensity
            )
            a = mask[:, :, None] * opacity
            current += (im - current) * a
        difference = current - self.small.astype(np.float32)
        frame = cv2.add(
            frame, cv2.resize(difference, frame.shape[1::-1]), dtype=cv2.CV_8U
        )
        if self.appearance > 0 and load_sprite("ghost") is not None:
            h, w = frame.shape[:2]
            source = load_sprite("ghost")
            height = max(32, round(h * 0.36))
            if height != self._appearance_size:
                self._appearance_sprite = cv2.resize(
                    source,
                    (round(height * source.shape[1] / source.shape[0]), height),
                    interpolation=cv2.INTER_AREA,
                )
                self._appearance_size = height
            paste_sprite(
                frame,
                self._appearance_sprite,
                w * 0.76,
                h * (0.46 + 0.025 * math.sin(self.time * 5)),
                min(0.8, self.appearance) * intensity,
            )
        elif self.appearance > 0:
            overlay = frame.copy()
            h, w = frame.shape[:2]
            cx = int(w * 0.76)
            cy = int(h * (0.43 + 0.025 * math.sin(self.time * 5)))
            r = max(12, w // 16)
            cv2.ellipse(
                overlay,
                (cx, cy),
                (r, int(r * 1.3)),
                0,
                0,
                360,
                (220, 245, 227),
                -1,
                cv2.LINE_AA,
            )
            pts = np.array(
                [
                    (cx - r, cy),
                    (cx - r, cy + r * 2),
                    (cx - r // 2, cy + int(r * 1.6)),
                    (cx, cy + r * 2),
                    (cx + r // 2, cy + int(r * 1.6)),
                    (cx + r, cy + r * 2),
                    (cx + r, cy),
                ]
            )
            cv2.fillPoly(overlay, [pts], (220, 245, 227), cv2.LINE_AA)
            for dx in (-r // 3, r // 3):
                cv2.ellipse(
                    overlay,
                    (cx + dx, cy),
                    (max(2, r // 8), max(3, r // 5)),
                    0,
                    0,
                    360,
                    (52, 49, 50),
                    -1,
                )
            a = min(0.65, self.appearance) * intensity
            frame = cv2.addWeighted(overlay, a, frame, 1 - a, 0)
        return frame
