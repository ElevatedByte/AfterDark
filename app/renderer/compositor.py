from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from app.tracking.models import BONES


def draw_debug(frame, people):
    for person in people:
        for a, b in BONES:
            pa, pb = person.point(a), person.point(b)
            if pa and pb:
                cv2.line(
                    frame,
                    pa.pixel(frame),
                    pb.pixel(frame),
                    (80, 255, 120),
                    2,
                    cv2.LINE_AA,
                )
        for p in person.landmarks.values():
            if p.confidence >= 0.35:
                cv2.circle(frame, p.pixel(frame), 3, (40, 180, 255), -1)
        if person.head:
            x, y = person.head.pixel(frame)
            cv2.putText(
                frame,
                f"ID {person.id}",
                (x, max(20, y - 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (80, 255, 120),
                2,
            )
    return frame


STANDBY_ART = (
    Path(__file__).resolve().parents[1] / "assets/backgrounds/haunted-house-standby.png"
)
STANDBY_TITLE = "The Dance Floor Awaits"


@lru_cache(maxsize=1)
def _load_standby_art():
    # The image is bundled with the app; runtime never downloads artwork.
    return cv2.imread(str(STANDBY_ART)) if STANDBY_ART.is_file() else None


def _centered_text(frame, text, y, background=False):
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_DUPLEX
    thickness = max(1, round(h / 450))
    scale = max(0.3, h / 650)
    size, baseline = cv2.getTextSize(text, font, scale, thickness)
    scale *= min(1.0, w * 0.88 / max(1, size[0]))
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = (w - tw) // 2, round(h * y)
    if background:
        padding = max(5, round(h * 0.013))
        cv2.rectangle(
            frame,
            (max(0, x - padding), max(0, y - th - padding)),
            (min(w - 1, x + tw + padding), min(h - 1, y + baseline + padding)),
            (30, 17, 27),
            -1,
        )
    cv2.putText(
        frame, text, (x, y), font, scale, (205, 232, 255), thickness, cv2.LINE_AA
    )


@lru_cache(maxsize=3)
def _standby_background(width, height):
    frame = np.full((height, width, 3), (30, 17, 27), np.uint8)
    artwork = _load_standby_art()
    if artwork is None:
        # Missing/corrupt artwork must never stop the camera or show runtime.
        _centered_text(frame, "The Dance Floor", 0.48)
        _centered_text(frame, "Awaits", 0.58)
        return frame
    ah, aw = artwork.shape[:2]
    aspect = width / height
    # The generated title has safe margins for the normal 4:3 and 16:9 formats.
    # Preserve the complete image for unusual aspect ratios so text stays visible.
    fit = max if 4 / 3 <= aspect <= 16 / 9 + 0.01 else min
    scale = fit(width / aw, height / ah)
    sw, sh = max(1, round(aw * scale)), max(1, round(ah * scale))
    fitted = cv2.resize(
        artwork,
        (sw, sh),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
    )
    cw, ch = min(width, sw), min(height, sh)
    sx, sy = (sw - cw) // 2, (sh - ch) // 2
    dx, dy = (width - cw) // 2, (height - ch) // 2
    frame[dy : dy + ch, dx : dx + cw] = fitted[sy : sy + ch, sx : sx + cw]
    return frame


def standby_frame(width, height, message=STANDBY_TITLE):
    # Cue rendering mutates frames; give it a fresh copy of the cached background.
    frame = _standby_background(width, height).copy()
    if message.casefold() != STANDBY_TITLE.casefold():
        _centered_text(frame, message, 0.94, background=True)
    return frame


def camera_viewport(frame, width, height):
    """Upscale only the video, before effects draw at projector pixel density."""
    h, w = frame.shape[:2]
    ratio = min(width / w, height / h)
    vw, vh = min(width, max(1, round(w * ratio))), min(height, max(1, round(h * ratio)))
    view = cv2.resize(
        frame, (vw, vh), interpolation=cv2.INTER_LINEAR if ratio > 1 else cv2.INTER_AREA
    )
    return view, ((width - vw) // 2, (height - vh) // 2)


def letterbox_output(view, width, height, offset):
    x, y = offset
    if view.shape[:2] == (height, width):
        return view
    vh, vw = view.shape[:2]
    output = np.empty((height, width, 3), np.uint8)
    # Fill just the bars: filling the full 1080p/4K array then overwriting its
    # center wastes memory bandwidth on every frame.
    color = (15, 10, 20)
    output[:y] = color
    output[y + vh :] = color
    output[y : y + vh, :x] = color
    output[y : y + vh, x + vw :] = color
    output[y : y + vh, x : x + vw] = view
    return output
