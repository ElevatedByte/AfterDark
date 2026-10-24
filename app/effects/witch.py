"""A green witch with a crooked purple hat and a golden buckle."""

import cv2
import numpy as np

from app.effects.character_art import INK, ellipse, eye, line, polygon
from app.effects.head_overlay import HeadOverlay
from app.renderer.sprites import load_sprite


class Witch(HeadOverlay):
    name = "witch"
    anchor = (0.5, 250 / 340)
    shoulder_scale = 1.35

    def create_asset(self):
        image = load_sprite(self.name)
        if image is not None:
            self.anchor = (0.48, 0.72)
            return image
        image = np.zeros((340, 280, 4), np.uint8)
        purple = (128, 53, 83, 255)
        green = (98, 192, 134, 255)
        gold = (58, 181, 249, 255)
        polygon(
            image,
            [
                (64, 174),
                (205, 175),
                (234, 309),
                (199, 297),
                (188, 327),
                (139, 309),
                (94, 328),
                (88, 303),
                (46, 314),
            ],
            (72, 40, 57, 255),
        )
        ellipse(image, (140, 242), (68, 76), green)
        ellipse(image, (83, 260), (13, 9), (99, 163, 133, 255), 0)
        ellipse(image, (194, 260), (13, 9), (99, 163, 133, 255), 0)
        eye(image, (112, 231))
        eye(image, (165, 231))
        line(image, [(95, 207), (111, 202), (124, 206)])
        line(image, [(153, 205), (169, 201), (181, 207)])
        polygon(image, [(138, 236), (158, 263), (128, 260)], (86, 173, 115, 255), 3)
        ellipse(image, (153, 258), (4, 4), INK, 0)
        cv2.ellipse(image, (140, 269), (25, 19), 0, 10, 165, INK, 4, cv2.LINE_AA)
        ellipse(image, (140, 181), (130, 23), purple)
        polygon(
            image,
            [(55, 177), (111, 44), (166, 12), (190, 39), (151, 37), (197, 177)],
            purple,
        )
        polygon(image, [(64, 154), (75, 129), (188, 143), (196, 176)], gold, 3)
        polygon(image, [(115, 140), (149, 145), (146, 170), (112, 165)], INK, 0)
        polygon(image, [(122, 148), (141, 151), (140, 161), (120, 158)], gold, 0)
        line(image, [(127, 68), (91, 121)], (167, 83, 120, 255), 5)
        return image
