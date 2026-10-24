"""A wrapped mummy with glowing eyes and loose linen tails."""

import numpy as np

from app.effects.character_art import CREAM, ellipse, eye, line, polygon
from app.effects.head_overlay import HeadOverlay
from app.renderer.sprites import load_sprite


class Mummy(HeadOverlay):
    name = "mummy"
    anchor = (0.5, 138 / 260)
    shoulder_scale = 1.0

    def create_asset(self):
        image = load_sprite(self.name)
        if image is not None:
            self.anchor = (0.5, 0.7)
            return image
        image = np.zeros((260, 220, 4), np.uint8)
        linen = (174, 218, 233, 255)
        shadow = (125, 167, 188, 255)
        seam = (106, 141, 161, 255)
        polygon(
            image,
            [
                (145, 178),
                (191, 202),
                (195, 229),
                (209, 239),
                (178, 248),
                (171, 217),
                (139, 203),
            ],
            linen,
            3,
        )
        line(image, [(175, 221), (194, 214)], seam, 2)
        polygon(
            image,
            [(62, 184), (47, 224), (30, 239), (21, 228), (32, 210), (39, 178)],
            linen,
            3,
        )
        ellipse(image, (110, 131), (78, 109), shadow)
        # Overlapping ribbons stay inside the head silhouette.
        polygon(
            image,
            [(45, 72), (62, 45), (108, 24), (154, 43), (172, 64), (174, 79), (100, 66)],
            linen,
            3,
        )
        polygon(
            image, [(37, 89), (45, 70), (179, 82), (186, 110), (112, 104)], CREAM, 3
        )
        polygon(
            image,
            [(34, 111), (38, 90), (105, 102), (176, 93), (184, 111), (114, 128)],
            linen,
            3,
        )
        ellipse(image, (110, 139), (63, 32), (55, 65, 61, 255), 3)
        for x in (81, 138):
            ellipse(image, (x, 137), (22, 24), (120, 170, 118, 255), 0)
            eye(image, (x, 137), (14, 18))
        polygon(
            image,
            [(35, 162), (101, 153), (184, 169), (177, 193), (108, 177), (39, 186)],
            CREAM,
            3,
        )
        polygon(
            image,
            [(45, 191), (111, 176), (177, 184), (167, 210), (92, 204), (54, 208)],
            linen,
            3,
        )
        polygon(
            image, [(58, 213), (167, 212), (145, 232), (111, 240), (83, 232)], CREAM, 3
        )
        line(image, [(61, 54), (162, 65)], seam, 2)
        line(image, [(58, 86), (156, 95)], seam, 2)
        line(image, [(53, 172), (99, 165)], seam, 2)
        line(image, [(102, 193), (158, 197)], seam, 2)
        line(image, [(87, 226), (132, 227)], seam, 2)
        return image
