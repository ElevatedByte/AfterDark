"""Seeded scenery on a perspective ground plane, with a clear central floor."""

import random

import cv2
import numpy as np

from app.effects.head_overlay import overlay
from app.renderer.sprites import load_sprite


SCENERY_COUNTS = {
    "scenery_houses": 2,
    "scenery_graves": 6,
    "scenery_pumpkins": 8,
    "scenery_trees": 0,
}


def layout(snapshot):
    rng = random.Random(snapshot["scenery_seed"])
    items = []
    sides = [0, 1]
    rng.shuffle(sides)
    for side in sides[: snapshot["scenery_houses"]]:
        width = rng.uniform(0.24, 0.275)
        height = rng.uniform(0.47, 0.57)
        ground = rng.uniform(0.71, 0.79)
        x = rng.uniform(0.008, 0.285 - width)
        if side:
            x = 1 - x - width
        items.append(
            dict(
                kind="scenery_house",
                x=x,
                y=ground - height,
                w=width,
                h=height,
                flip=bool(side),
            )
        )
    kinds = ["gravestone"] * snapshot["scenery_graves"] + [
        "scenery_pumpkin"
    ] * snapshot["scenery_pumpkins"]
    rng.shuffle(kinds)
    # Sample continuous positions, preferring open ground footprints. Overlapping
    # silhouettes are natural here: near objects draw in front of distant ones.
    for kind in kinds:
        candidates = []
        for _ in range(64):
            ground = rng.uniform(0.79, 0.982)
            depth = (ground - 0.70) / 0.282
            scale = rng.uniform(0.65, 1.35) * (0.48 + 0.65 * depth)
            width = min(0.14, 0.10 * scale)
            height = (0.23 if kind == "gravestone" else 0.16) * scale
            x = rng.uniform(0.012, 0.285 - width)
            if rng.random() < 0.5:
                x = 1 - x - width
            cx = x + width / 2
            score = 0
            for other in items:
                if other["kind"] == "scenery_house":
                    continue
                dx = abs(cx - (other["x"] + other["w"] / 2))
                dy = abs(ground - (other["y"] + other["h"]))
                # Keep bases separated, but permit believable depth occlusion.
                score += max(0, 1 - dx / ((width + other["w"]) * 0.45)) * max(
                    0, 1 - dy / 0.035
                )
            candidates.append(
                (
                    score,
                    dict(
                        kind=kind,
                        x=x,
                        y=ground - height,
                        w=width,
                        h=height,
                        flip=rng.choice([False, True]),
                    ),
                )
            )
        items.append(min(candidates, key=lambda candidate: candidate[0])[1])
    # Append trees after sampling the existing props so adding/removing trees
    # preserves the rest of a saved layout. Alternate wings, with varied roots.
    tree_sides = [0, 1]
    rng.shuffle(tree_sides)
    for index in range(snapshot.get("scenery_trees", 0)):
        side = tree_sides[index % 2]
        candidates = []
        for _ in range(48):
            width = rng.uniform(0.14, 0.195)
            height = rng.uniform(0.46, 0.64)
            ground = rng.uniform(0.78, 0.88)
            x = rng.uniform(0.006, 0.285 - width)
            if side:
                x = 1 - x - width
            cx = x + width / 2
            score = sum(
                max(0, 1 - abs(cx - (other["x"] + other["w"] / 2)) / 0.10)
                * max(0, 1 - abs(ground - other["y"] - other["h"]) / 0.08)
                for other in items
            )
            candidates.append(
                (
                    score,
                    dict(
                        kind="scenery_tree",
                        x=x,
                        y=ground - height,
                        w=width,
                        h=height,
                        flip=bool(side),
                    ),
                )
            )
        items.append(min(candidates, key=lambda candidate: candidate[0])[1])
    return sorted(items, key=lambda item: item["y"] + item["h"])


def contact_shadow(width, height):
    """Soft elliptical contact shadow, sized to an object's ground footprint."""
    y, x = np.mgrid[-1 : 1 : complex(height), -1 : 1 : complex(width)]
    alpha = np.clip(1 - x * x - y * y, 0, 1) ** 1.5 * 125
    shadow = np.zeros((height, width, 4), np.uint8)
    shadow[:, :, 3] = alpha.astype(np.uint8)
    return shadow


class Scenery:
    def __init__(self):
        self.key = None
        self.sprites = []
        self.webs = []

    def render(self, frame, snapshot):
        if not snapshot["scenery_enabled"]:
            return frame
        h, w = frame.shape[:2]
        key = (
            w,
            h,
            snapshot["scenery_seed"],
            snapshot.get("scenery_webs", "none"),
            *(snapshot[name] for name in SCENERY_COUNTS),
        )
        if key != self.key:
            self.sprites = []
            for item in layout(snapshot):
                asset = load_sprite(item["kind"])
                if asset is None:
                    continue
                # Atlas tiles have padding; place the actual silhouette on ground.
                points = cv2.findNonZero((asset[:, :, 3] > 8).astype(np.uint8))
                if points is None:
                    continue
                ax, ay, aw, ah = cv2.boundingRect(points)
                asset = asset[ay : ay + ah, ax : ax + aw]
                ratio = min(item["w"] * w / aw, item["h"] * h / ah)
                sw, sh = max(1, round(aw * ratio)), max(1, round(ah * ratio))
                sprite = cv2.resize(asset, (sw, sh), interpolation=cv2.INTER_AREA)
                if item["flip"]:
                    sprite = cv2.flip(sprite, 1)
                # Ground the sprite at the bottom of its allotted cell.
                cx = (item["x"] + item["w"] / 2) * w
                cy = (item["y"] + item["h"]) * h - sh / 2
                shadow = contact_shadow(
                    max(3, round(sw * 0.92)), max(3, round(sh * 0.10))
                )
                ground = (item["y"] + item["h"]) * h
                self.sprites.append((sprite, cx, cy, shadow, ground))
            self.webs = []
            mode = snapshot.get("scenery_webs", "none")
            asset = load_sprite("scenery_web") if mode != "none" else None
            if asset is not None:
                ah, aw = asset.shape[:2]
                ratio = min(0.26 * w / aw, 0.40 * h / ah)
                sw, sh = max(1, round(aw * ratio)), max(1, round(ah * ratio))
                web = cv2.resize(asset, (sw, sh), interpolation=cv2.INTER_AREA)
                if mode in ("left", "both"):
                    self.webs.append((web, sw / 2, sh / 2))
                if mode in ("right", "both"):
                    self.webs.append((cv2.flip(web, 1), w - sw / 2, sh / 2))
            self.key = key
        for sprite, cx, cy, shadow, ground in self.sprites:
            overlay(frame, shadow, cx, ground - shadow.shape[0] * 0.25)
            overlay(frame, sprite, cx, cy)
        for sprite, cx, cy in self.webs:
            overlay(frame, sprite, cx, cy)
        return frame
