import math
from functools import lru_cache
import cv2
import numpy as np
from app.effects.particles import ParticleEffect
from app.effects.head_overlay import overlay
from app.renderer.sprites import load_sprite


@lru_cache(maxsize=192)
def bat_frame(width, flap, angle):
    source = load_sprite("bat")
    if source is None:
        return None
    height = max(4, round(width * source.shape[0] / source.shape[1] * (0.4 + flap / 5)))
    sprite = cv2.resize(source, (width, height), interpolation=cv2.INTER_AREA)
    radians = math.radians(angle)
    rw = math.ceil(abs(width * math.cos(radians)) + abs(height * math.sin(radians)))
    rh = math.ceil(abs(height * math.cos(radians)) + abs(width * math.sin(radians)))
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    matrix[:, 2] += ((rw - width) / 2, (rh - height) / 2)
    return cv2.warpAffine(sprite, matrix, (rw, rh))


class Bats(ParticleEffect):
    name = "bats"
    cap = 180

    def on_hand(self, hand, speed, dt, key):
        if speed > 0.65:
            self.emit_rate(
                hand,
                25 * speed * self.settings.get("particle_amount", 0.55),
                dt,
                key,
                0.30,
            )

    def render(self, frame):
        intensity = self.settings.get("effect_intensity", 0.75)
        if not self.particles or intensity <= 0:
            return frame
        h, w = frame.shape[:2]
        if load_sprite("bat") is not None:
            for p in self.particles:
                fade = max(0, 1 - p.age / p.life)
                width = max(16, round(w * 0.053 * (0.5 + fade * 0.5) / 8) * 8)
                flap = round(1.5 + 1.5 * math.sin(p.age * 20 + p.phase))
                angle = (
                    round((math.sin(p.age * 3) * 12 + math.sin(p.phase) * 12) / 10) * 10
                )
                sprite = bat_frame(width, flap, angle)
                overlay(frame, sprite, p.x * w, p.y * h, intensity * min(1, fade * 3))
            return frame
        layer = frame.copy()
        for p in self.particles:
            size = max(4, int(w * 0.019 * (1 - p.age / p.life * 0.5)))
            flap = 0.5 + 0.5 * math.sin(p.age * 20 + p.phase)
            points = (
                np.array(
                    [
                        (-1.4, -0.8 * flap),
                        (-0.65, -0.3),
                        (-0.22, 0),
                        (0, -0.35),
                        (0.22, 0),
                        (0.65, -0.3),
                        (1.4, -0.8 * flap),
                        (1, 0.3),
                        (0.65, 0.05),
                        (0.35, 0.4),
                        (0, 0.65),
                        (-0.35, 0.4),
                        (-0.65, 0.05),
                        (-1, 0.3),
                    ]
                )
                * size
            )
            angle = p.phase * 0.2 + math.sin(p.age * 3) * 0.15
            matrix = np.array(
                [
                    [math.cos(angle), -math.sin(angle)],
                    [math.sin(angle), math.cos(angle)],
                ]
            )
            points = (points @ matrix + np.array([p.x * w, p.y * h])).astype(np.int32)
            cv2.fillPoly(layer, [points], (66, 27, 42), cv2.LINE_AA)
            cv2.polylines(layer, [points], True, (188, 120, 179), 1, cv2.LINE_AA)
        intensity = self.settings.get("effect_intensity", 0.75)
        return cv2.addWeighted(layer, intensity, frame, 1 - intensity, 0)
