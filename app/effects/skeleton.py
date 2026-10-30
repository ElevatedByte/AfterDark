"""Resolution-independent articulated bones with a detailed, face-anchored skull."""

import math
import cv2
import numpy as np
from app.effects.head_overlay import HeadOverlay
from app.renderer.sprites import load_sprite
from app.tracking.models import BONES, Point


class Skeleton(HeadOverlay):
    name = "skeleton"
    anchor = (0.5, 0.64)
    shoulder_scale = 0.72

    def create_asset(self):
        image = load_sprite("skull")
        if image is not None:
            return image
        image = np.zeros((256, 224, 4), np.uint8)
        cv2.ellipse(
            image,
            (112, 115),
            (98, 108),
            0,
            0,
            360,
            (190, 244, 230, 255),
            -1,
            cv2.LINE_AA,
        )
        cv2.rectangle(image, (60, 173), (165, 247), (190, 244, 230, 255), -1)
        for x in (72, 152):
            cv2.ellipse(
                image, (x, 120), (27, 31), 0, 0, 360, (30, 37, 27, 255), -1, cv2.LINE_AA
            )
        for x in range(76, 160, 23):
            cv2.line(image, (x, 215), (x, 247), (30, 37, 27, 255), 4, cv2.LINE_AA)
        return image

    def render_body(self, frame):
        intensity = self.settings.get("effect_intensity", 0.75)
        if not self.people or intensity <= 0:
            return frame
        layer = frame.copy()
        bone, shadow, highlight = (180, 218, 231), (71, 88, 115), (223, 241, 248)
        for p in self.people:
            ls, rs = p.shoulders
            lh, rh = p.hips
            shoulder = (
                math.dist(ls.pixel(frame), rs.pixel(frame))
                if ls and rs
                else frame.shape[1] * 0.14
            )
            thickness = max(3, round(shoulder * 0.045))
            for a, b in BONES:
                pa, pb = p.point(a), p.point(b)
                if pa and pb:
                    start, end = pa.pixel(layer), pb.pixel(layer)
                    cv2.line(
                        layer,
                        start,
                        end,
                        shadow,
                        thickness + max(2, thickness // 3),
                        cv2.LINE_AA,
                    )
                    cv2.line(layer, start, end, bone, thickness, cv2.LINE_AA)
                    cv2.line(
                        layer,
                        start,
                        end,
                        highlight,
                        max(1, thickness // 3),
                        cv2.LINE_AA,
                    )
                    for joint in (start, end):
                        cv2.circle(
                            layer,
                            joint,
                            max(2, thickness * 2 // 3),
                            shadow,
                            -1,
                            cv2.LINE_AA,
                        )
                        cv2.circle(
                            layer, joint, max(1, thickness // 2), bone, -1, cv2.LINE_AA
                        )
            if all((ls, rs, lh, rh)):
                top = Point((ls.x + rs.x) / 2, (ls.y + rs.y) / 2)
                bottom = Point((lh.x + rh.x) / 2, (lh.y + rh.y) / 2)
                angle = (
                    math.degrees(
                        math.atan2(
                            (rs.y - ls.y) * frame.shape[0],
                            (rs.x - ls.x) * frame.shape[1],
                        )
                    )
                    % 180
                )
                cv2.line(
                    layer,
                    top.pixel(layer),
                    bottom.pixel(layer),
                    shadow,
                    thickness + 3,
                    cv2.LINE_AA,
                )
                cv2.line(
                    layer,
                    top.pixel(layer),
                    bottom.pixel(layer),
                    bone,
                    thickness,
                    cv2.LINE_AA,
                )
                for t in (0.16, 0.29, 0.42, 0.55, 0.68):
                    center = Point(
                        top.x * (1 - t) + bottom.x * t, top.y * (1 - t) + bottom.y * t
                    ).pixel(layer)
                    width = max(6, round(shoulder * (0.43 - 0.20 * t)))
                    axes = (width, max(3, round(width * 0.26)))
                    for color, stroke in (
                        (shadow, thickness),
                        (bone, max(2, thickness - 2)),
                        (highlight, max(1, thickness // 4)),
                    ):
                        cv2.ellipse(
                            layer,
                            center,
                            axes,
                            angle,
                            10,
                            170,
                            color,
                            stroke,
                            cv2.LINE_AA,
                        )
        frame = cv2.addWeighted(layer, intensity, frame, 1 - intensity, 0)
        return frame

    def render(self, frame):
        return super().render(self.render_body(frame))
