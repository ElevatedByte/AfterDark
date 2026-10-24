"""A cheerful flat-topped monster, complete with neck bolts and stitches."""

import cv2
import numpy as np

from app.effects.character_art import CREAM, INK, ellipse, eye, line, polygon
from app.effects.head_overlay import HeadOverlay
from app.renderer.sprites import load_sprite


class Frankenstein(HeadOverlay):
    name = "frankenstein"
    anchor = (0.5, 145 / 260)
    shoulder_scale = 1.02

    def create_asset(self):
        image = load_sprite(self.name)
        if image is not None:
            self.anchor = (0.5, 0.59)
            return image
        image = np.zeros((260, 240, 4), np.uint8)
        green = (114, 186, 128, 255)
        steel = (174, 182, 187, 255)
        polygon(
            image, [(69, 222), (84, 249), (156, 249), (171, 222)], (105, 62, 76, 255)
        )
        for x in (20, 199):
            polygon(image, [(x, 191), (x + 21, 191), (x + 21, 207), (x, 207)], steel, 3)
            polygon(image, [(x, 186), (x + 8, 186), (x + 8, 212), (x, 212)], steel, 3)
        ellipse(image, (42, 147), (17, 25), green)
        ellipse(image, (198, 147), (17, 25), green)
        polygon(
            image,
            [(46, 43), (194, 43), (191, 207), (165, 231), (75, 231), (48, 207)],
            green,
        )
        polygon(
            image,
            [
                (45, 84),
                (46, 26),
                (194, 26),
                (195, 83),
                (179, 67),
                (166, 79),
                (151, 65),
                (136, 78),
                (120, 62),
                (105, 77),
                (89, 66),
                (73, 80),
                (60, 67),
            ],
            (48, 39, 39, 255),
        )
        line(image, [(62, 45), (171, 45)], (78, 66, 59, 255), 5)
        line(image, [(132, 94), (177, 99)], INK, 3)
        for x in (142, 155, 168):
            line(image, [(x, 89), (x - 2, 103)], INK, 3)
        eye(image, (87, 142), (17, 19))
        eye(image, (152, 142), (17, 19))
        line(image, [(67, 119), (94, 114)], INK, 7)
        line(image, [(139, 115), (170, 119)], INK, 7)
        line(image, [(120, 146), (112, 170), (130, 170)], (62, 116, 75, 255), 4)
        cv2.ellipse(image, (121, 181), (31, 19), 0, 5, 175, INK, 4, cv2.LINE_AA)
        polygon(image, [(113, 199), (113, 188), (125, 188), (125, 200)], CREAM, 2)
        line(image, [(67, 170), (71, 183)], INK, 3)
        line(image, [(62, 176), (76, 173)], INK, 2)
        return image
