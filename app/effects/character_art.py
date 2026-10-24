"""Small OpenCV drawing helpers for the original, friendly character artwork."""

import cv2
import numpy as np

INK = (38, 27, 32, 255)
CREAM = (215, 244, 255, 255)


def polygon(image, points, color, stroke=4):
    points = np.array(points, np.int32)
    cv2.fillPoly(image, [points], color, cv2.LINE_AA)
    if stroke:
        cv2.polylines(image, [points], True, INK, stroke, cv2.LINE_AA)


def ellipse(image, center, axes, color, stroke=4, angle=0):
    cv2.ellipse(image, center, axes, angle, 0, 360, color, -1, cv2.LINE_AA)
    if stroke:
        cv2.ellipse(image, center, axes, angle, 0, 360, INK, stroke, cv2.LINE_AA)


def line(image, points, color=INK, thickness=4):
    cv2.polylines(
        image, [np.array(points, np.int32)], False, color, thickness, cv2.LINE_AA
    )


def eye(image, center, axes=(15, 19), pupil_offset=(0, 2)):
    ellipse(image, center, axes, CREAM, 3)
    x, y = center
    ellipse(image, (x + pupil_offset[0], y + pupil_offset[1]), (6, 9), INK, 0)
    ellipse(image, (x - 2, y - 2), (2, 3), (255, 255, 255, 255), 0)
