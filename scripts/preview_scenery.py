"""Render a reproducible scenery preview without camera or display access."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
from app.config import Config
from app.renderer.compositor import standby_frame
from app.renderer.scenery import Scenery
from app.state.app_state import AppState

state = AppState(Config())
snapshot = state.snapshot()
snapshot.update(
    scenery_enabled=True, scenery_seed=204, scenery_trees=2, scenery_webs="both"
)
frame = Scenery().render(standby_frame(1920, 1080), snapshot)
path = Path("artifacts/scenery-preview.png")
path.parent.mkdir(exist_ok=True)
cv2.imwrite(str(path), frame)
print(path)
