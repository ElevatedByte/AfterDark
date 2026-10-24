"""Thread-safe state. Public snapshots never contain arrays or mutable references."""

from copy import deepcopy
from app.cues.catalog import LIVE_CUES
import random
from queue import Queue, Full
from threading import RLock
from pydantic import BaseModel, ConfigDict, Field

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
    fullscreen: bool | None = None
    debug_skeleton: bool | None = None
    effect_intensity: float | None = Field(None, ge=0, le=1)
    ghost_trail_strength: float | None = Field(None, ge=0, le=1)
    particle_amount: float | None = Field(None, ge=0, le=1)
    tracking_smoothing: float | None = Field(None, ge=0, le=0.95)
    projector_monitor_index: int | None = Field(None, ge=0, le=15)
    max_people: int | None = Field(None, ge=1, le=8)
    adaptive_resolution: bool | None = None


class AppState:
    def __init__(self, config):
        self._lock = RLock()
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

    def set_effect(self, name, enabled):
        if name not in EFFECTS:
            raise ValueError(f"Unknown effect: {name}")
        with self._lock:
            active = set(self._data["active_effects"])
            active.add(name) if enabled else active.discard(name)
            self.update(active_effects=[e for e in EFFECTS if e in active])

    def settings(self, patch: SettingsPatch):
        values = patch.model_dump(exclude_none=True)
        with self._lock:
            effects = self._data["effect_settings"].copy()
            for key in tuple(values):
                if key in effects:
                    effects[key] = values.pop(key)
            self.update(effect_settings=effects, **values)

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
