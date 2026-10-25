"""Environment configuration; no network activity during application startup."""

import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent.parent


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    camera_index: int = 0
    camera_width: int = Field(1280, ge=320, le=3840)
    camera_height: int = Field(720, ge=240, le=2160)
    output_width: int = Field(1920, ge=320, le=3840)
    output_height: int = Field(1080, ge=240, le=2160)
    projector_monitor: int = Field(1, ge=0, le=15)
    max_people: int = Field(8, ge=1, le=8)
    pose_confidence: float = Field(0.5, ge=0.1, le=1)
    tracking_smoothing: float = Field(0.65, ge=0, le=0.95)
    fullscreen: bool = True
    mirror_camera: bool = True
    auto_start_camera: bool = True
    adaptive_resolution: bool = True
    low_fps_threshold: float = Field(20, ge=1, le=60)
    target_fps: int = Field(30, ge=5, le=60)
    segmentation: bool = True
    model_path: Path = ROOT / "app/assets/models/pose_landmarker_lite.task"
    host: str = "127.0.0.1"
    port: int = Field(8000, ge=1024, le=65535)
    demo_mode: bool = False
    random_show: bool = False
    settings_path: Path | None = None
    hands_above_duration: float = Field(0.6, ge=0.1, le=5)
    hands_together_distance: float = Field(0.10, ge=0.02, le=0.4)
    gesture_cooldown: float = Field(2, ge=0.2, le=10)
    jump_threshold: float = Field(0.055, ge=0.01, le=0.3)
    track_timeout: float = Field(1.2, ge=0.1, le=5)

    @classmethod
    def from_env(cls):
        return cls(
            **{
                name: os.environ[name.upper()]
                for name in cls.model_fields
                if name.upper() in os.environ
            }
        )
