"""Thread-safe state. Public snapshots never contain arrays or mutable references."""

from copy import deepcopy
import logging
from app.cues.catalog import LIVE_CUES
from app.cues.automation import AUTO_CATALOG, AUTO_TRIGGERS
import random
from queue import Queue, Full, Empty
from threading import RLock
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.state.storage import read_settings, write_settings

log = logging.getLogger(__name__)

CHARACTER_EFFECTS = ("witch", "frankenstein", "vampire", "mummy")
EFFECTS = (
    "pumpkin_head",
    *CHARACTER_EFFECTS,
    "skeleton",
    "bats",
    "ghost",
    "magic",
    "lightning",
)

# Person-attached effects; lightning is a full-screen event.
RANDOM_PERSON_EFFECTS = tuple(name for name in EFFECTS if name != "lightning")
SCENES = {
    "normal_camera": [],
    "pumpkin_dance": ["pumpkin_head", "bats"],
    "skeleton_dance": ["skeleton", "lightning"],
    "ghost_mode": ["ghost"],
    "magic_mode": ["magic", "lightning"],
}
TRIGGERS = (
    "lightning",
    "spawn_bats",
    "ghost_appearance",
    "scream",
    "spell_burst",
    *LIVE_CUES,
    "stop_animations",
    "reset_scene",
    "reset_tracking",
)


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    random_show: bool | None = None
    random_min_seconds: float | None = Field(None, ge=1, le=300)
    random_max_seconds: float | None = Field(None, ge=1, le=300)
    random_triggers: list[str] | None = Field(None, max_length=len(AUTO_TRIGGERS))
    fullscreen: bool | None = None
    debug_skeleton: bool | None = None
    effect_intensity: float | None = Field(None, ge=0, le=1)
    ghost_trail_strength: float | None = Field(None, ge=0, le=1)
    particle_amount: float | None = Field(None, ge=0, le=1)
    tracking_smoothing: float | None = Field(None, ge=0, le=0.95)
    projector_monitor_index: int | None = Field(None, ge=0, le=15)
    max_people: int | None = Field(None, ge=1, le=8)
    adaptive_resolution: bool | None = None

    @field_validator("random_triggers")
    @classmethod
    def valid_random_triggers(cls, value):
        if value is None:
            return value
        if any(name not in AUTO_TRIGGERS for name in value):
            raise ValueError("Unknown automatic visitor or effect")
        return [name for name in AUTO_TRIGGERS if name in value]

    def validate_timing(self, minimum=3, maximum=10):
        low = (
            self.random_min_seconds if self.random_min_seconds is not None else minimum
        )
        high = (
            self.random_max_seconds if self.random_max_seconds is not None else maximum
        )
        if low > high:
            raise ValueError(
                "Minimum delay must be less than or equal to maximum delay"
            )


class SavedShow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    active_scene: str
    active_effects: list[str]
    settings: SettingsPatch

    @model_validator(mode="after")
    def valid_timing(self):
        self.settings.validate_timing()
        return self

    @field_validator("active_scene")
    @classmethod
    def valid_scene(cls, value):
        if value not in SCENES:
            raise ValueError("Unknown saved scene")
        return value

    @field_validator("active_effects")
    @classmethod
    def valid_effects(cls, value):
        if any(name not in EFFECTS for name in value):
            raise ValueError("Unknown saved effect")
        return list(dict.fromkeys(value))


class AppState:
    def __init__(self, config):
        self._lock = RLock()
        self._settings_path = config.settings_path
        self.commands = Queue(maxsize=64)
        self._data = dict(
            camera_requested=config.auto_start_camera,
            camera_running=False,
            camera_connected=False,
            camera_error=None,
            projector_requested=False,
            projector_running=False,
            projector_error=None,
            projector_driver=None,
            projector_fullscreen=False,
            projector_monitor_actual=None,
            fullscreen=config.fullscreen,
            debug_skeleton=False,
            random_show=config.random_show,
            random_min_seconds=3.0,
            random_max_seconds=10.0,
            random_triggers=list(AUTO_TRIGGERS),
            auto_catalog=AUTO_CATALOG,
            last_auto_trigger=None,
            settings_persistence=config.settings_path is not None,
            settings_save_error=None,
            active_scene="normal_camera",
            active_effects=[],
            active_cues=[],
            cue_catalog=LIVE_CUES,
            effect_settings=dict(
                effect_intensity=0.75,
                ghost_trail_strength=0.65,
                particle_amount=0.55,
                tracking_smoothing=config.tracking_smoothing,
            ),
            tracked_people_count=0,
            people=[],
            person_effects={},
            fps=0.0,
            frame_latency_ms=0.0,
            projector_monitor_index=config.projector_monitor,
            max_people=config.max_people,
            camera_resolution=[config.camera_width, config.camera_height],
            output_resolution=[config.output_width, config.output_height],
            adaptive_resolution=config.adaptive_resolution,
            resolution_reduced=False,
            tracking_status="idle",
            tracking_error=None,
            runtime_error=None,
            renderer_backend="cpu",
            renderer_timings={},
            preview_dropped=0,
            preview_error=None,
            demo_mode=config.demo_mode,
            last_gesture=None,
            revision=0,
            scene_revision=0,
            tracking_revision=0,
        )
        self._restore_settings()

    def _apply_settings(self, values):
        effects = self._data["effect_settings"].copy()
        for key in tuple(values):
            if key in effects:
                effects[key] = values.pop(key)
        self.update(effect_settings=effects, **values)

    def _restore_settings(self):
        if self._settings_path is None:
            return
        try:
            saved = SavedShow.model_validate(read_settings(self._settings_path))
        except FileNotFoundError:
            self._save_settings()
        except (OSError, ValueError) as exc:
            log.warning("Could not load show settings: %s", exc)
            self.update(
                settings_save_error="Saved settings could not be loaded; using defaults."
            )
        else:
            self.update(
                active_scene=saved.active_scene, active_effects=saved.active_effects
            )
            self._apply_settings(saved.settings.model_dump(exclude_none=True))

    def _save_settings(self):
        # Called under the state lock so concurrent controllers cannot save stale values.
        if self._settings_path is None:
            return
        settings = {
            key: self._data[key]
            for key in SettingsPatch.model_fields
            if key in self._data
        }
        settings.update(self._data["effect_settings"])
        saved = SavedShow(
            active_scene=self._data["active_scene"],
            active_effects=self._data["active_effects"],
            settings=SettingsPatch(**settings),
        )
        try:
            write_settings(self._settings_path, saved.model_dump())
        except OSError as exc:
            log.warning("Could not save show settings: %s", exc)
            self.update(
                settings_save_error="Changes are active but could not be saved for restart."
            )
        else:
            self.update(settings_save_error=None)

    def set_show(self, running):
        with self._lock:
            if not running:
                while True:
                    try:
                        self.commands.get_nowait()
                    except Empty:
                        break
                # Reset transient effects on the processing thread, even with camera off.
                self.update(scene_revision=self._data["scene_revision"] + 1)
            self.update(
                camera_requested=running,
                projector_requested=running,
                random_show=running,
                camera_error=None,
                projector_error=None,
            )
            self._save_settings()

    def trigger_automatic(self, name):
        with self._lock:
            if (
                not self._data["random_show"]
                or name not in self._data["random_triggers"]
            ):
                return
            try:
                self.commands.put_nowait(name)
            except Full:
                return
            self.update(last_auto_trigger=name)

    def snapshot(self):
        with self._lock:
            return deepcopy(self._data)

    def update(self, **values):
        with self._lock:
            unknown = values.keys() - self._data.keys()
            if unknown:
                raise ValueError(f"Unknown state keys: {unknown}")
            self._data.update(deepcopy(values))
            self._data["revision"] += 1

    def set_scene(self, name):
        if name not in SCENES:
            raise ValueError(f"Unknown scene: {name}")
        with self._lock:
            self.update(
                active_scene=name,
                active_effects=list(SCENES[name]),
                person_effects={},
                scene_revision=self._data["scene_revision"] + 1,
            )
            self._save_settings()

    def set_effect(self, name, enabled):
        if name not in EFFECTS:
            raise ValueError(f"Unknown effect: {name}")
        with self._lock:
            active = set(self._data["active_effects"])
            active.add(name) if enabled else active.discard(name)
            self.update(active_effects=[e for e in EFFECTS if e in active])
            self._save_settings()

    def settings(self, patch: SettingsPatch):
        values = patch.model_dump(exclude_none=True)
        with self._lock:
            patch.validate_timing(
                self._data["random_min_seconds"], self._data["random_max_seconds"]
            )
            self._apply_settings(values)
            self._save_settings()

    def sync_person_effects(self, new_person_ids, retained_person_ids):
        """Set Normal Camera defaults once; preserve manual choices in every mode."""
        with self._lock:
            assignments = {
                key: value
                for key, value in self._data["person_effects"].items()
                if int(key) in retained_person_ids
            }
            if self._data["active_scene"] == "normal_camera":
                for person_id in sorted(new_person_ids):
                    key = str(person_id)
                    if key not in assignments:
                        assignments[key] = [random.choice(RANDOM_PERSON_EFFECTS)]
            if assignments != self._data["person_effects"]:
                self.update(person_effects=assignments)
            return deepcopy(assignments)

    def assign_person(self, person_id, effects):
        if effects is not None and any(e not in EFFECTS for e in effects):
            raise ValueError("Unknown effect")
        with self._lock:
            if person_id not in [p["id"] for p in self._data["people"]]:
                raise ValueError("Person is no longer tracked")
            assignments = self._data["person_effects"].copy()
            if effects is None:
                assignments.pop(str(person_id), None)
            else:
                assignments[str(person_id)] = list(dict.fromkeys(effects))
            self.update(person_effects=assignments)

    def trigger(self, name):
        if name not in TRIGGERS:
            raise ValueError(f"Unknown trigger: {name}")
        if name == "stop_animations":
            self.settings(SettingsPatch(random_show=False))
        if name == "reset_scene":
            self.set_scene("normal_camera")
        elif name == "reset_tracking":
            with self._lock:
                self.update(
                    tracking_revision=self._data["tracking_revision"] + 1,
                    person_effects={},
                )
        else:
            try:
                self.commands.put_nowait(name)
            except Full:
                raise ValueError("Trigger queue is full; try again shortly")
