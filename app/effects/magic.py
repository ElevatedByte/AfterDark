"""Additive, soft-glowing star particles drawn at projector resolution."""

from functools import lru_cache
import math
import cv2
import numpy as np
from app.effects.particles import ParticleEffect


@lru_cache(maxsize=96)
def star_sprite(size, violet):
    yy, xx = np.mgrid[-1 : 1 : complex(size), -1 : 1 : complex(size)]
    radius = np.hypot(xx, yy)
    glow = np.exp(-radius * radius * 7) * 0.28
    rays = np.exp(-np.minimum(abs(xx), abs(yy)) * 70) * np.maximum(0, 1 - radius) ** 1.5
    diagonals = (
        np.exp(-np.minimum(abs(xx - yy), abs(xx + yy)) * 85)
        * np.maximum(0, 0.6 - radius)
        * 0.7
    )
    color = np.array((255, 146, 208) if violet else (101, 221, 255))
    rgb = (glow + rays + diagonals)[:, :, None] * color
    rgb += np.exp(-radius * radius * 250)[:, :, None] * 255
    return np.clip(rgb, 0, 255).astype(np.uint8)


class Magic(ParticleEffect):
    name = "magic"

    def on_hand(self, hand, speed, dt, key):
        self.emit_rate(
            hand,
            (10 + speed * 95) * self.settings.get("particle_amount", 0.55),
            dt,
            key,
            0.05 + min(0.35, speed * 0.1),
        )

    def render(self, frame):
        intensity = self.settings.get("effect_intensity", 0.75)
        if not self.particles or intensity <= 0:
            return frame
        h, w = frame.shape[:2]
        for p in self.particles:
            fade = max(0, 1 - p.age / p.life)
            size = max(12, round(w * 0.024 * (0.4 + fade * 0.6) / 4) * 4)
            x, y = round(p.x * w - size / 2), round(p.y * h - size / 2)
            x1, y1, x2, y2 = max(0, x), max(0, y), min(w, x + size), min(h, y + size)
            if x1 >= x2 or y1 >= y2:
                continue
            star = star_sprite(size, p.phase >= math.pi)[
                y1 - y : y2 - y, x1 - x : x2 - x
            ]
            brightness = intensity * fade * (0.8 + 0.2 * math.sin(p.age * 12 + p.phase))
            cv2.add(
                frame[y1:y2, x1:x2],
                cv2.convertScaleAbs(star, alpha=brightness),
                dst=frame[y1:y2, x1:x2],
            )
        return frame
