"""Finite, frame-rate-independent cues with bounded sprites and no pose dependency."""

from abc import abstractmethod
import math

import cv2

from app.effects.base import Effect
from app.effects.head_overlay import overlay
from app.cues.catalog import LIVE_CUES


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def rise_and_fall(progress, enter=0.25, leave=0.72):
    return ease(progress / enter) * (1 - ease((progress - leave) / (1 - leave)))


class TimedCue(Effect):
    def initialize(self):
        self.duration = LIVE_CUES[self.name]["duration"]
        self.elapsed = self.duration
        self.assets = self.create_assets()
        self._scaled = {}
        self._frame_size = None

    @abstractmethod
    def create_assets(self):
        """Build original BGRA art once, not inside the rendering loop."""

    def reset(self):
        super().reset()
        self.elapsed = self.duration

    @property
    def alive(self):
        return self.elapsed < self.duration

    @property
    def progress(self):
        return min(1.0, self.elapsed / self.duration)

    def trigger(self, people=None):
        # One instance per cue: repeated taps restart instead of piling up objects.
        self.elapsed = 0.0
        self.time = 0.0

    def update(self, frame, tracking_data, delta_time):
        super().update(frame, [], delta_time)
        self.elapsed = min(self.duration, self.elapsed + max(0.0, delta_time))
        size = frame.shape[:2]
        if size != self._frame_size:
            self._scaled.clear()
            self._frame_size = size

    @property
    def opacity(self):
        fade = min(1.0, self.elapsed / 0.2, (self.duration - self.elapsed) / 0.35)
        return max(0.0, fade) * self.settings.get("effect_intensity", 0.75)

    def draw(self, frame, key, x, y, height, angle=0, alpha=1.0, flip=False):
        """Place a cached sprite in normalized screen coordinates; retain its aspect."""
        h, w = frame.shape[:2]
        asset = self.assets[key]
        # Restrict size on portrait inputs too. Camera and projector sizes may differ.
        pixels = max(
            1, round(min(h * height, w * 0.85 * asset.shape[0] / asset.shape[1]))
        )
        if hasattr(frame, "sprite"):
            frame.sprite(
                asset,
                x * w,
                y * h,
                max(1, round(asset.shape[1] * pixels / asset.shape[0])),
                pixels,
                angle=angle,
                alpha=self.opacity * alpha,
                flip=flip,
            )
            return
        cache_key = (key, pixels, flip)
        if cache_key not in self._scaled:
            sw = max(1, round(asset.shape[1] * pixels / asset.shape[0]))
            sprite = cv2.resize(
                asset,
                (sw, pixels),
                interpolation=cv2.INTER_AREA
                if pixels < asset.shape[0]
                else cv2.INTER_LANCZOS4,
            )
            self._scaled[cache_key] = cv2.flip(sprite, 1) if flip else sprite
        sprite = self._scaled[cache_key]
        if angle:
            sh, sw = sprite.shape[:2]
            radians = math.radians(angle)
            rw = math.ceil(abs(sw * math.cos(radians)) + abs(sh * math.sin(radians)))
            rh = math.ceil(abs(sh * math.cos(radians)) + abs(sw * math.sin(radians)))
            matrix = cv2.getRotationMatrix2D((sw / 2, sh / 2), angle, 1)
            matrix[:, 2] += ((rw - sw) / 2, (rh - sh) / 2)
            sprite = cv2.warpAffine(sprite, matrix, (rw, rh))
        overlay(frame, sprite, x * w, y * h, self.opacity * alpha)

    def render(self, frame):
        if self.alive and self.opacity > 0:
            self.animate(frame)
        return frame

    @abstractmethod
    def animate(self, frame): ...
