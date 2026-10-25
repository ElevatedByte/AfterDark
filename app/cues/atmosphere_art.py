"""Matching sprite assets with small procedural fallbacks for offline resilience."""

import cv2
import numpy as np

from app.renderer.sprites import sprite_asset


@sprite_asset("fog_bank")
def fog_bank():
    y, x = np.mgrid[0:160, 0:600].astype(np.float32)
    density = np.zeros_like(x)
    for cx, cy, sx, sy in (
        (100, 85, 75, 24),
        (220, 80, 95, 38),
        (370, 98, 110, 30),
        (490, 76, 65, 22),
    ):
        density += np.exp(-(((x - cx) / sx) ** 2) - ((y - cy) / sy) ** 2) * 0.45
    image = np.empty((160, 600, 4), np.uint8)
    image[:, :, :3] = (222, 199, 201)
    image[:, :, 3] = np.clip(density * 190, 0, 210).astype(np.uint8)
    return image


@sprite_asset("haunted_eyes")
def haunted_eyes():
    image = np.zeros((100, 280, 4), np.uint8)
    for x in (75, 205):
        cv2.ellipse(
            image, (x, 50), (53, 30), 0, 0, 360, (104, 58, 95, 150), -1, cv2.LINE_AA
        )
        cv2.ellipse(
            image, (x, 50), (44, 22), 0, 0, 360, (85, 203, 242, 255), -1, cv2.LINE_AA
        )
        cv2.ellipse(
            image, (x, 50), (6, 19), 0, 0, 360, (38, 20, 33, 255), -1, cv2.LINE_AA
        )
        cv2.circle(image, (x - 13, 42), 5, (235, 252, 255, 255), -1, cv2.LINE_AA)
    return image


@sprite_asset("portal_ring")
def portal_ring():
    image = np.zeros((400, 400, 4), np.uint8)
    for radius, width, color in (
        (166, 28, (171, 78, 148, 70)),
        (158, 15, (214, 135, 146, 190)),
        (153, 5, (219, 244, 190, 255)),
    ):
        cv2.circle(image, (200, 200), radius, color, width, cv2.LINE_AA)
    for angle in range(0, 360, 45):
        cv2.ellipse(
            image,
            (200, 200),
            (162, 155),
            angle,
            5,
            29,
            (130, 213, 255, 240),
            5,
            cv2.LINE_AA,
        )
    return image
