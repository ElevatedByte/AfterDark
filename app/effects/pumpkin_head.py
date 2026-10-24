import cv2
import numpy as np
from app.effects.head_overlay import HeadOverlay
from app.renderer.sprites import sprite_asset, load_sprite


@sprite_asset("pumpkin_head")
def pumpkin_asset():
    image = np.zeros((160, 180, 4), np.uint8)
    cv2.rectangle(image, (83, 4), (98, 34), (38, 94, 74, 255), -1)
    for x, color in [
        (61, (12, 100, 222, 255)),
        (119, (8, 94, 211, 255)),
        (90, (20, 137, 253, 255)),
    ]:
        cv2.ellipse(image, (x, 88), (47, 61), 0, 0, 360, color, -1, cv2.LINE_AA)
    for x in (61, 119):
        cv2.fillConvexPoly(
            image,
            np.array([(x - 15, 79), (x + 13, 80), (x + 6, 58)]),
            (13, 25, 39, 255),
            cv2.LINE_AA,
        )
    cv2.fillConvexPoly(
        image, np.array([(88, 80), (78, 96), (100, 96)]), (13, 25, 39, 255), cv2.LINE_AA
    )
    cv2.fillPoly(
        image,
        [
            np.array(
                [
                    (47, 105),
                    (65, 117),
                    (73, 110),
                    (84, 120),
                    (97, 113),
                    (107, 118),
                    (133, 102),
                    (123, 132),
                    (64, 136),
                ]
            )
        ],
        (13, 25, 39, 255),
        cv2.LINE_AA,
    )
    return image


class PumpkinHead(HeadOverlay):
    name = "pumpkin_head"

    def create_asset(self):
        if load_sprite(self.name) is not None:
            self.anchor = (0.5, 0.64)
        return pumpkin_asset()
