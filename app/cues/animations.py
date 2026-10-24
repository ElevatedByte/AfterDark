"""Seven small timelines. All motion is based on elapsed seconds, not frame count."""

import math
import cv2

from app.cues import art
from app.cues.base import TimedCue, rise_and_fall
from app.effects.pumpkin_head import pumpkin_asset
from app.renderer.sprites import load_sprite


class SkeletonPeek(TimedCue):
    name = "skeleton_peek"

    def create_assets(self):
        return {
            "stone": art.gravestone(),
            "skeleton": art.skeleton(),
            "hand": art.skeleton_hand(),
        }

    def animate(self, frame):
        lift = rise_and_fall(self.progress, 0.32, 0.65)
        # Paint the skeleton first; the stone occludes it as it ducks back down.
        self.draw(
            frame,
            "skeleton",
            0.26,
            1.18 - 0.56 * lift,
            0.40,
            angle=3 * math.sin(self.elapsed * 7) * lift,
        )
        if lift > 0.7 and load_sprite("skeleton") is None:
            self.draw(
                frame,
                "hand",
                0.33,
                0.50 + 0.025 * math.sin(self.elapsed * 9),
                0.13,
                angle=22 * math.sin(self.elapsed * 9),
            )
        self.draw(frame, "stone", 0.26, 0.89, 0.36)


class WitchFlyby(TimedCue):
    name = "witch_flyby"

    def create_assets(self):
        return {"witch": art.flying_witch()}

    def animate(self, frame):
        p = self.progress
        self.draw(
            frame,
            "witch",
            -0.25 + 1.5 * p,
            0.30 + 0.065 * math.sin(p * math.tau),
            0.34,
            angle=-10 * math.cos(p * math.tau),
        )


class GhostParade(TimedCue):
    name = "ghost_parade"

    def create_assets(self):
        return {"ghost": art.ghost()}

    def animate(self, frame):
        for i in range(3):
            x = -0.22 + 1.8 * self.progress - i * 0.15
            self.draw(
                frame,
                "ghost",
                x,
                0.43 + 0.055 * math.sin(self.elapsed * 3 + i),
                0.27 - i * 0.025,
                angle=6 * math.sin(self.elapsed * 3 + i),
                alpha=0.85,
            )


class PumpkinRoll(TimedCue):
    name = "pumpkin_roll"

    def create_assets(self):
        return {"pumpkin": pumpkin_asset()}

    def animate(self, frame):
        p = self.progress
        x = -0.18 + 1.36 * p
        self.draw(
            frame,
            "pumpkin",
            x,
            0.83 - 0.05 * abs(math.sin(p * 5 * math.pi)),
            0.24,
            angle=-p * 1080,
        )


class SpiderDrop(TimedCue):
    name = "spider_drop"

    def create_assets(self):
        return {"spider": art.spider()}

    def animate(self, frame):
        lift = rise_and_fall(self.progress, 0.30, 0.62)
        x = 0.74 + 0.02 * math.sin(self.elapsed * 3) * lift
        y = -0.19 + 0.63 * lift
        h, w = frame.shape[:2]
        # A narrow ROI avoids copying the entire camera frame just for the silk.
        if y > 0:
            x1, x2 = max(0, int((x - 0.035) * w)), min(w, int((x + 0.035) * w) + 1)
            y2 = min(h, max(1, int(y * h)))
            roi = frame[:y2, x1:x2]
            silk = roi.copy()
            cv2.line(
                silk,
                (int(0.74 * w) - x1, 0),
                (int(x * w) - x1, y2),
                (210, 225, 229),
                max(1, round(w / 640)),
                cv2.LINE_AA,
            )
            cv2.addWeighted(silk, self.opacity, roi, 1 - self.opacity, 0, roi)
        self.draw(
            frame, "spider", x, y, 0.27, angle=7 * math.sin(self.elapsed * 8) * lift
        )


class ZombieHands(TimedCue):
    name = "zombie_hands"

    def create_assets(self):
        return {"hand": art.zombie_hand(), "dirt": art.dirt()}

    def animate(self, frame):
        for i, x in enumerate((0.44, 0.61)):
            p = max(0, (self.progress - i * 0.06) / (1 - i * 0.06))
            lift = rise_and_fall(p, 0.3, 0.65)
            self.draw(
                frame,
                "hand",
                x,
                1.22 - 0.41 * lift,
                0.43,
                flip=bool(i),
                angle=(4 * math.sin(self.elapsed * 6 + i)) * lift,
            )
        self.draw(frame, "dirt", 0.52, 0.985, 0.11)


class BlackCat(TimedCue):
    name = "black_cat"

    def create_assets(self):
        return {"cat": art.cat(), "blink": art.cat(True), "moon": art.moon()}

    def animate(self, frame):
        lift = rise_and_fall(self.progress, 0.25, 0.70)
        self.draw(
            frame,
            "moon",
            0.79,
            0.70,
            0.46,
            alpha=lift * (0.68 + 0.10 * math.sin(self.elapsed * 3)),
        )
        blink = 2.0 < self.elapsed % 3.0 < 2.22
        self.draw(
            frame,
            "blink" if blink else "cat",
            0.79,
            1.25 - 0.46 * lift + 0.006 * math.sin(self.elapsed * 4) * lift,
            0.42,
        )


def create_cues():
    return {
        cue.name: cue
        for cue in (
            SkeletonPeek(),
            WitchFlyby(),
            GhostParade(),
            PumpkinRoll(),
            SpiderDrop(),
            ZombieHands(),
            BlackCat(),
        )
    }
