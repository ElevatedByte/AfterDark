"""Cached transparent artwork. Atlas regions are unpacked once at startup."""

from functools import lru_cache, wraps
from pathlib import Path
import cv2
import numpy as np

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets/overlays"
# The generator packs objects with slightly irregular gutters. Use their actual
# bounds rather than assuming an exact grid and cutting off hats or broom tips.
REGIONS = {
    "pumpkin_head": ("heads", (34, 7, 503, 500)),
    "witch": ("heads", (515, 1, 1048, 531)),
    "frankenstein": ("heads", (1083, 47, 1496, 517)),
    "vampire": ("heads", (29, 506, 519, 995)),
    "mummy": ("heads", (552, 519, 985, 991)),
    "skull": ("heads", (1107, 531, 1462, 993)),
    "flying_witch": ("visitors", (14, 8, 610, 460)),
    "ghost": ("visitors", (628, 37, 1026, 474)),
    "spider": ("visitors", (1026, 98, 1520, 456)),
    "zombie_hand": ("visitors", (140, 483, 420, 1014)),
    "cat": ("visitors", (561, 479, 924, 999)),
    "gravestone": ("visitors", (1047, 497, 1501, 991)),
    "skeleton": ("details", (19, 23, 517, 533)),
    "skeleton_hand": ("details", (612, 53, 909, 490)),
    "bat": ("details", (917, 138, 1536, 443)),
    "dirt": ("details", (4, 739, 522, 905)),
    "moon": ("details", (558, 520, 990, 950)),
    "cat_blink": ("visitors-blink", (561, 479, 924, 999)),
}


@lru_cache(maxsize=4)
def _atlas(name):
    path = ASSET_DIR / (name + ".png")
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED) if path.is_file() else None
    if image is None or image.ndim != 3 or image.shape[2] != 4:
        return None
    return image


@lru_cache(maxsize=len(REGIONS))
def load_sprite(name):
    atlas, (x1, y1, x2, y2) = REGIONS[name]
    image = _atlas(atlas)
    if image is None:
        return None
    tile = image[y1:y2, x1:x2].copy()
    # Neighboring sprites can extend into a rectangular atlas region. Keep its
    # main connected silhouette plus antialiased edge pixels, not its neighbors.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        (tile[:, :, 3] > 16).astype(np.uint8)
    )
    if count < 2:
        return None
    selected = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    keep = cv2.dilate((labels == selected).astype(np.uint8), np.ones((7, 7), np.uint8))
    tile[:, :, 3] *= keep
    tile.flags.writeable = False
    return tile


def sprite_asset(name):
    """Retain code-drawn artwork as a fallback for missing/corrupt asset packs."""

    def decorate(factory):
        @wraps(factory)
        def asset(*args, **kwargs):
            image = load_sprite(name)
            return image if image is not None else factory(*args, **kwargs)

        return asset

    return decorate
