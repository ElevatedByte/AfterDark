"""Render actual 1080p effects/cues and time composition separately from inference."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import copy
    import json
    import math
    import time
    import cv2
    import numpy as np
    from app.config import Config
    from app.camera.demo import DemoCamera
    from app.cues.animations import create_cues
    from app.effects.manager import EffectManager
    from app.renderer.compositor import standby_frame
    from app.runtime import Runtime
    from app.state.app_state import AppState, EFFECTS, SettingsPatch
    from app.tracking.models import Point

    cv2.setNumThreads(2)
    target = ROOT / "artifacts/hd"
    target.mkdir(parents=True, exist_ok=True)
    config = Config(demo_mode=True, camera_width=640, camera_height=480)
    camera = DemoCamera(config)
    camera.start()
    camera.start_time = time.monotonic() - 0.2
    packet = camera.latest()
    people = camera.people
    for i, person in enumerate(people, 1):
        person.id = i
    preview = np.full((1080, 1920, 3), (34, 27, 38), np.uint8)
    person = copy.deepcopy(people[0])
    head = person.head
    for name, point in list(person.landmarks.items()):
        person.landmarks[name] = Point(
            0.5 + (point.x - head.x) * 2.2, 0.46 + (point.y - head.y), point.confidence
        )
    person.segmentation_mask = cv2.resize(person.segmentation_mask, (1920, 1080))
    manager = EffectManager()
    panels = []
    for name in (
        "pumpkin_head",
        "witch",
        "frankenstein",
        "vampire",
        "mummy",
        "skeleton",
        "bats",
        "ghost",
        "magic",
        "lightning",
    ):
        effect = manager.effects[name]
        effect.settings = {
            "effect_intensity": 1,
            "particle_amount": 0.7,
            "ghost_trail_strength": 0.8,
        }
        effect.trigger([person])
        frame = preview.copy()
        effect.update(frame, [person], 0.035)
        if name in ("bats", "magic"):
            effect.reset()
            effect.trigger([])
            for step in range(20):
                effect.update(frame, [], 0.02)
        frame = effect.render(frame)
        cv2.imwrite(
            str(target / (name + ".jpg")), frame, [cv2.IMWRITE_JPEG_QUALITY, 96]
        )
        # Show the actual face-sized crop, without enlarging the rendered pixels.
        if name in (
            "pumpkin_head",
            "witch",
            "frankenstein",
            "vampire",
            "mummy",
            "skeleton",
        ):
            panel = frame[0:810, 555:1365]
            panel = cv2.resize(panel, (480, 480), interpolation=cv2.INTER_AREA)
        else:
            panel = cv2.resize(frame, (480, 270), interpolation=cv2.INTER_AREA)
            panel = cv2.copyMakeBorder(
                panel, 105, 105, 0, 0, cv2.BORDER_CONSTANT, value=(34, 27, 38)
            )
        panel = cv2.copyMakeBorder(
            panel, 0, 36, 0, 0, cv2.BORDER_CONSTANT, value=(24, 20, 28)
        )
        cv2.putText(
            panel,
            name.replace("_", " ").title(),
            (18, 505),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (205, 219, 237),
            1,
            cv2.LINE_AA,
        )
        panels.append(panel)
    while len(panels) % 5:
        panels.append(np.zeros_like(panels[0]))
    sheet = np.vstack([np.hstack(panels[i : i + 5]) for i in range(0, len(panels), 5)])
    cv2.imwrite(
        str(ROOT / "artifacts/hd-overlays-preview.jpg"),
        sheet,
        [cv2.IMWRITE_JPEG_QUALITY, 95],
    )
    cues = create_cues()
    for name, cue in cues.items():
        frame = standby_frame(1920, 1080, "The Dance Floor Awaits")
        cue.settings = {"effect_intensity": 1}
        cue.trigger()
        cue.update(frame, [], cue.duration * 0.45)
        cv2.imwrite(
            str(target / (name + ".jpg")),
            cue.render(frame),
            [cv2.IMWRITE_JPEG_QUALITY, 96],
        )

    report = {
        "camera": [640, 480],
        "output": [1920, 1080],
        "inference": "excluded; fixed synthetic poses",
        "cases": {},
    }
    for label, names, count, with_cues in [
        (
            "four_characters",
            ["pumpkin_head", "witch", "frankenstein", "mummy"],
            4,
            False,
        ),
        ("skeleton_dance", ["skeleton"], 4, False),
        ("ghost_trails", ["ghost"], 4, False),
        ("magic_and_bats", ["magic", "bats"], 4, False),
        ("all_effects_and_visitors", list(EFFECTS), 4, True),
    ]:
        state = AppState(config)
        state.set_scene("ghost_mode")
        for effect in EFFECTS:
            state.set_effect(effect, effect in names)
        state.settings(SettingsPatch(effect_intensity=0.85, particle_amount=0.55))
        runtime = Runtime(config, state)
        if label == "four_characters":
            state.update(
                person_effects={str(i + 1): [name] for i, name in enumerate(names)}
            )
        dancers = []
        for i in range(count):
            dancer = copy.deepcopy(people[i % len(people)])
            original_x = dancer.head.x
            for name, point in list(dancer.landmarks.items()):
                dancer.landmarks[name] = Point(
                    (i + 0.5) / count + (point.x - original_x) * 0.75,
                    point.y,
                    point.confidence,
                )
            dancer.bounding_box = ((i + 0.1) / count, 0.1, (i + 0.9) / count, 0.95)
            dancers.append(dancer)
        if with_cues:
            for name in cues:
                state.trigger(name)
        for name in ("spawn_bats", "spell_burst", "ghost_appearance"):
            if with_cues or label == "magic_and_bats":
                state.trigger(name)
        times = []
        for step in range(90):
            for i, dancer in enumerate(dancers):
                for name, sign in (("left_hand", -1), ("right_hand", 1)):
                    dancer.landmarks[name] = Point(
                        (i + 0.5) / count + sign * 0.08 + 0.03 * math.sin(step * 0.2),
                        0.4 + 0.07 * math.cos(step * 0.2),
                    )
            started = time.perf_counter()
            output, _ = runtime.process_frame(
                packet.color, dancers, 1 / 30, step / 30, state.snapshot(), True
            )
            if step >= 15:
                times.append((time.perf_counter() - started) * 1000)
        assert output.shape == (1080, 1920, 3)
        report["cases"][label] = {
            "median_ms": round(float(np.median(times)), 2),
            "p95_ms": round(float(np.percentile(times, 95)), 2),
        }
        print(label, report["cases"][label], flush=True)
    (ROOT / "artifacts/hd-render-performance.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
    print("Rendered frames:", target)


if __name__ == "__main__":
    main()
