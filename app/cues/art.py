"""Original OpenCV character sprites for the live show cues."""

import cv2
import numpy as np

from app.effects.character_art import CREAM, INK, ellipse, eye, line, polygon
from app.effects.witch import Witch
from app.renderer.sprites import sprite_asset, load_sprite


def canvas(width, height):
    return np.zeros((height, width, 4), np.uint8)


def paste(image, sprite, x, y, width):
    # Art construction only: source-over preserves alpha on transparent canvases.
    height = round(sprite.shape[0] * width / sprite.shape[1])
    sprite = cv2.resize(sprite, (width, height), interpolation=cv2.INTER_AREA)
    roi = image[y : y + height, x : x + width]
    sa = sprite[:, :, 3:4].astype(np.float32) / 255
    da = roi[:, :, 3:4].astype(np.float32) / 255
    alpha = sa + da * (1 - sa)
    rgb = (sprite[:, :, :3] * sa + roi[:, :, :3] * da * (1 - sa)) / np.maximum(
        alpha, 1e-6
    )
    roi[:, :, :3] = rgb.astype(np.uint8)
    roi[:, :, 3:4] = (alpha * 255).astype(np.uint8)


@sprite_asset("gravestone")
def gravestone():
    image = canvas(300, 250)
    ellipse(image, (150, 89), (86, 73), (132, 142, 153, 255))
    polygon(image, [(64, 90), (236, 90), (239, 224), (61, 224)], (132, 142, 153, 255))
    line(image, [(78, 95), (79, 207), (221, 207)], (172, 180, 184, 255), 4)
    cv2.putText(
        image, "RIP", (97, 136), cv2.FONT_HERSHEY_SIMPLEX, 1.1, INK, 3, cv2.LINE_AA
    )
    line(image, [(158, 157), (146, 173), (164, 181), (151, 204)], (78, 88, 98, 255), 3)
    ellipse(image, (150, 229), (143, 15), (69, 91, 89, 255), 0)
    for x in (31, 53, 230, 266):
        line(
            image,
            [(x - 8, 233), (x - 10, 207), (x, 227), (x + 8, 211)],
            (94, 138, 121, 255),
            3,
        )
    return image


@sprite_asset("skeleton")
def skeleton():
    image = canvas(250, 280)
    # Arms and ribcage are revealed behind the stone as the skull rises.
    for points in (
        [(125, 130), (125, 248)],
        [(121, 149), (65, 166), (34, 224)],
        [(129, 149), (189, 168), (218, 111)],
    ):
        line(image, points, INK, 15)
        line(image, points, CREAM, 9)
    for y in (167, 188, 209):
        cv2.ellipse(image, (125, y), (32, 12), 0, 0, 180, CREAM, 8, cv2.LINE_AA)
    ellipse(image, (125, 75), (56, 59), CREAM)
    polygon(image, [(87, 98), (163, 98), (157, 137), (94, 137)], CREAM)
    for x in (103, 147):
        ellipse(image, (x, 75), (15, 19), INK, 0)
        ellipse(image, (x + 2, 72), (5, 6), (196, 222, 190, 255), 0)
    polygon(image, [(125, 92), (117, 107), (133, 107)], INK, 0)
    line(image, [(98, 121), (153, 121)], INK, 3)
    for x in (107, 119, 131, 143):
        line(image, [(x, 115), (x, 133)], INK, 2)
    return image


@sprite_asset("skeleton_hand")
def skeleton_hand():
    image = canvas(80, 100)
    for end in ((12, 30), (25, 13), (43, 8), (60, 16), (72, 40)):
        line(image, [(40, 88), (40, 52), end], INK, 12)
        line(image, [(40, 88), (40, 52), end], CREAM, 7)
    ellipse(image, (40, 56), (15, 17), CREAM, 2)
    return image


@sprite_asset("flying_witch")
def flying_witch():
    image = canvas(400, 290)
    # Straw, wooden broom handle, dress, boots, then the familiar witch face.
    polygon(
        image,
        [(40, 195), (101, 217), (63, 266), (12, 258), (28, 231), (13, 210)],
        (66, 170, 223, 255),
    )
    for y in (211, 225, 241, 255):
        line(image, [(33, y), (91, 219)], (44, 106, 162, 255), 3)
    line(image, [(77, 227), (363, 190)], INK, 14)
    line(image, [(77, 227), (363, 190)], (62, 127, 164, 255), 8)
    polygon(
        image,
        [(194, 149), (242, 164), (218, 221), (121, 217), (163, 180)],
        (123, 52, 85, 255),
    )
    line(image, [(207, 208), (246, 219), (259, 245), (281, 243)], INK, 12)
    line(image, [(222, 169), (262, 194), (282, 194)], INK, 14)
    line(image, [(222, 169), (262, 194), (282, 194)], (98, 192, 134, 255), 8)
    paste(image, Witch().asset, 147, 5, 139)
    return image


@sprite_asset("ghost")
def ghost():
    image = canvas(180, 230)
    color = (226, 245, 223, 255)
    ellipse(image, (90, 76), (66, 67), color, 0)
    polygon(
        image,
        [
            (24, 80),
            (156, 80),
            (167, 210),
            (137, 193),
            (115, 218),
            (88, 195),
            (63, 218),
            (40, 193),
            (13, 212),
        ],
        color,
        0,
    )
    # Outline the joined silhouette so no seam runs across the ghost's face.
    contours, _ = cv2.findContours(
        image[:, :, 3], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(image, contours, -1, INK, 3, cv2.LINE_AA)
    for x in (67, 113):
        ellipse(image, (x, 81), (12, 18), INK, 0)
        ellipse(image, (x - 3, 75), (3, 4), CREAM, 0)
    cv2.ellipse(image, (91, 120), (19, 14), 0, 5, 175, INK, 4, cv2.LINE_AA)
    return image


@sprite_asset("spider")
def spider():
    image = canvas(260, 220)
    for side in (-1, 1):
        for i in range(4):
            points = [
                (130 + side * 29, 92 + i * 14),
                (130 + side * (77 + i * 4), 37 + i * 37),
                (130 + side * (113 - i * 5), 21 + i * 52),
            ]
            line(image, points, INK, 14)
            line(image, points, (154, 85, 128, 255), 8)
    ellipse(image, (130, 81), (39, 49), (138, 66, 105, 255))
    ellipse(image, (130, 136), (49, 46), (170, 93, 152, 255))
    eye(image, (110, 128), (16, 20))
    eye(image, (151, 128), (16, 20))
    cv2.ellipse(image, (131, 151), (18, 13), 0, 0, 180, INK, 3, cv2.LINE_AA)
    return image


@sprite_asset("zombie_hand")
def zombie_hand():
    image = canvas(180, 280)
    green = (101, 181, 119, 255)
    polygon(
        image,
        [
            (66, 271),
            (60, 180),
            (34, 148),
            (10, 113),
            (17, 101),
            (35, 107),
            (53, 128),
            (41, 55),
            (46, 41),
            (59, 45),
            (75, 110),
            (68, 25),
            (76, 12),
            (89, 16),
            (98, 106),
            (106, 18),
            (121, 15),
            (129, 28),
            (124, 114),
            (145, 51),
            (159, 48),
            (168, 62),
            (143, 166),
            (124, 192),
            (136, 271),
        ],
        green,
    )
    for x, y in ((48, 51), (76, 26), (112, 29), (151, 63)):
        line(image, [(x, y), (x + 8, y + 2)], (155, 219, 194, 255), 5)
    line(image, [(80, 159), (100, 140), (124, 157)], (66, 127, 91, 255), 4)
    line(image, [(88, 215), (119, 208)], INK, 3)
    for x in (95, 105, 115):
        line(image, [(x, 204), (x + 2, 219)], INK, 2)
    polygon(
        image,
        [
            (60, 246),
            (81, 238),
            (98, 250),
            (121, 237),
            (137, 245),
            (138, 277),
            (60, 277),
        ],
        (100, 61, 81, 255),
    )
    return image


@sprite_asset("dirt")
def dirt():
    image = canvas(400, 70)
    ellipse(image, (200, 42), (193, 23), (61, 82, 106, 255), 0)
    for x in range(35, 380, 37):
        ellipse(image, (x, 32 + x % 17), (11, 7), (82, 111, 133, 255), 0)
    return image


def cat(blink=False):
    image = load_sprite("cat_blink" if blink else "cat")
    if image is not None:
        return image
    image = canvas(270, 300)
    outline = (159, 118, 187, 255)
    body = (50, 38, 53, 255)
    # A luminous outline makes the black silhouette readable on dark video.
    points = [(194, 260), (239, 247), (251, 210), (236, 181), (218, 187)]
    line(image, points, outline, 22)
    line(image, points, body, 14)
    ellipse(image, (123, 221), (67, 65), outline, 0)
    ellipse(image, (123, 221), (62, 60), body, 0)
    polygon(
        image,
        [
            (56, 118),
            (47, 24),
            (99, 60),
            (149, 61),
            (196, 24),
            (190, 120),
            (170, 160),
            (80, 160),
        ],
        outline,
        0,
    )
    polygon(
        image,
        [
            (61, 115),
            (53, 35),
            (98, 67),
            (151, 68),
            (191, 35),
            (185, 117),
            (166, 154),
            (83, 154),
        ],
        body,
        0,
    )
    polygon(image, [(62, 53), (69, 92), (86, 78)], (168, 99, 185, 255), 0)
    polygon(image, [(181, 53), (160, 80), (177, 92)], (168, 99, 185, 255), 0)
    for x in (91, 153):
        if blink:
            line(
                image, [(x - 18, 111), (x, 115), (x + 17, 110)], (125, 244, 203, 255), 4
            )
        else:
            ellipse(image, (x, 109), (22, 15), (125, 244, 203, 255), 0)
            ellipse(image, (x, 109), (4, 13), INK, 0)
    polygon(image, [(114, 127), (132, 127), (123, 137)], (168, 99, 185, 255), 0)
    for side in (-1, 1):
        for dy in (-8, 5):
            line(
                image, [(123 + side * 32, 136), (123 + side * 83, 136 + dy)], outline, 2
            )
    for x in (93, 154):
        ellipse(image, (x, 272), (27, 13), outline, 0)
        ellipse(image, (x, 270), (23, 10), body, 0)
    return image


@sprite_asset("moon")
def moon():
    image = canvas(300, 300)
    for radius in range(144, 109, -1):
        ellipse(
            image,
            (150, 150),
            (radius, radius),
            (199, 166, 232, round((145 - radius) * 2)),
            0,
        )
    ellipse(image, (150, 150), (110, 110), (194, 206, 243, 205), 0)
    for x, y, radius in ((120, 91, 17), (190, 145, 25), (113, 196, 13)):
        ellipse(image, (x, y), (radius, radius), (177, 183, 222, 130), 0)
    return image
