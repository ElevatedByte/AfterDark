"""Bounded synthetic CPU benchmark; dummy presentation is not hardware validation."""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.runtime import Runtime
from app.state.app_state import AppState, EFFECTS
from app.camera.demo import DemoCamera
from app.tracking.models import Point


class FourPoseDemo(DemoCamera):
    def latest(self):
        started = time.perf_counter()
        frame = super().latest()
        people = []
        # Four synthetic pose/mask producers over two painted demonstration
        # figures. This measures load, not four real people or visual accuracy.
        for index, person in enumerate(self.people * 2):
            offset = -0.06 if index < 2 else 0.06
            points = {
                name: Point(p.x + offset, p.y, p.confidence)
                for name, p in person.landmarks.items()
            }
            people.append(replace(person, id=index, landmarks=points))
        self.people = people
        self.generation_ms = (time.perf_counter() - started) * 1000
        return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument(
        "--output", type=Path, default=Path("work/runtime-benchmark.json")
    )
    args = parser.parse_args()
    config = Config(
        demo_mode=True,
        camera_width=640,
        camera_height=480,
        projector_monitor=0,
        fullscreen=False,
        adaptive_resolution=False,
    )
    state = AppState(config)
    runtime = Runtime(config, state)
    runtime.camera = FourPoseDemo(config)
    results = dict(
        kind="synthetic CPU; SDL dummy; not GPU/camera/projector acceptance",
        camera=[640, 480],
        output=[1920, 1080],
        poses=4,
        target_fps=30,
        cases={},
    )
    state.update(projector_requested=True)
    runtime.start()
    try:
        for case in ("normal", "all_effects_all_cues"):
            deadline = time.monotonic() + 2
            while len(state.snapshot()["people"]) < 4 and time.monotonic() < deadline:
                time.sleep(0.1)
            if case == "normal":
                for person in state.snapshot()["people"]:
                    state.assign_person(person["id"], ["pumpkin_head"])
            if case != "normal":
                state.set_scene("normal_camera")
                for effect in EFFECTS:
                    state.set_effect(effect, True)
                deadline = time.monotonic() + 2
                while (
                    len(state.snapshot()["people"]) < 4 and time.monotonic() < deadline
                ):
                    time.sleep(0.1)
                for person in state.snapshot()["people"]:
                    state.assign_person(person["id"], list(EFFECTS))
                for cue in runtime.effects.cues:
                    state.trigger(cue)
                state.trigger("lightning")
            # Reset sample windows after warm-up; keep thread-safe access.
            time.sleep(2)
            with runtime.metrics.lock:
                runtime.metrics.samples.clear()
            until = time.monotonic() + args.seconds
            while time.monotonic() < until:
                if case != "normal":
                    for cue in runtime.effects.cues:
                        state.trigger(cue)
                    state.trigger("lightning")
                    state.trigger("spawn_bats")
                    state.trigger("spell_burst")
                time.sleep(min(1, max(0, until - time.monotonic())))
            snapshot = state.snapshot()
            results["cases"][case] = dict(
                fps=snapshot["fps"],
                people=snapshot["tracked_people_count"],
                frame_age_ms=snapshot["frame_latency_ms"],
                synthetic_generation_last_ms=runtime.camera.generation_ms,
                timings=runtime.metrics.snapshot(),
                preview_dropped=runtime.encoder.dropped,
                runtime_error=snapshot["runtime_error"],
                projector_driver=snapshot["projector_driver"],
            )
    finally:
        runtime.stop()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
