"""A smiling vampire with pointed ears, little fangs and a red cape collar."""

import numpy as np

from app.effects.character_art import CREAM, INK, ellipse, eye, line, polygon
from app.effects.head_overlay import HeadOverlay
from app.renderer.sprites import load_sprite


class Vampire(HeadOverlay):
    name = "vampire"
    anchor = (0.5, 143 / 300)
    shoulder_scale = 1.12

    def create_asset(self):
        image = load_sprite(self.name)
        if image is not None:
            self.anchor = (0.5, 0.63)
            return image
        image = np.zeros((300, 240, 4), np.uint8)
        skin = (228, 210, 226, 255)
        polygon(
            image,
            [
                (12, 173),
                (65, 195),
                (120, 235),
                (174, 195),
                (228, 173),
                (192, 263),
                (120, 289),
                (48, 263),
            ],
            (68, 46, 65, 255),
        )
        polygon(
            image, [(23, 185), (77, 208), (111, 267), (57, 250)], (81, 63, 209, 255), 3
        )
        polygon(
            image,
            [(217, 185), (163, 208), (129, 267), (183, 250)],
            (81, 63, 209, 255),
            3,
        )
        polygon(image, [(100, 225), (140, 225), (120, 278)], CREAM, 3)
        polygon(
            image,
            [(101, 251), (119, 256), (139, 251), (137, 267), (121, 261), (103, 267)],
            INK,
            2,
        )
        polygon(image, [(54, 117), (16, 91), (30, 154), (57, 167)], skin)
        polygon(image, [(186, 117), (224, 91), (210, 154), (183, 167)], skin)
        line(image, [(28, 111), (41, 142)], (161, 123, 177, 255), 4)
        line(image, [(212, 111), (199, 142)], (161, 123, 177, 255), 4)
        ellipse(image, (120, 136), (71, 94), skin)
        polygon(
            image,
            [
                (49, 132),
                (42, 79),
                (57, 39),
                (93, 20),
                (145, 20),
                (183, 39),
                (198, 79),
                (191, 133),
                (174, 78),
                (141, 69),
                (120, 94),
                (99, 69),
                (67, 78),
            ],
            (50, 34, 46, 255),
        )
        line(image, [(71, 53), (95, 40), (140, 40)], (90, 67, 88, 255), 5)
        eye(image, (91, 133), (16, 19), (1, 2))
        eye(image, (149, 133), (16, 19), (-1, 2))
        line(image, [(75, 110), (101, 105)], INK, 4)
        line(image, [(137, 105), (165, 111)], INK, 4)
        line(image, [(121, 139), (112, 159), (126, 159)], (170, 140, 180, 255), 3)
        ellipse(image, (120, 184), (31, 18), (83, 47, 92, 255), 3)
        polygon(image, [(95, 175), (108, 175), (106, 192)], CREAM, 2)
        polygon(image, [(132, 175), (145, 175), (134, 192)], CREAM, 2)
        return image
