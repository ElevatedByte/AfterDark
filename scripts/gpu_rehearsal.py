"""Opt-in, hardware-only GPU head/cue rehearsal; does not replace the full show."""

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.camera.demo import DemoCamera
from app.config import Config
from app.renderer.gpu_process import GpuProjector, HEADS, encode_people
from app.cues.catalog import LIVE_CUES
from app.tracking.person_tracker import PersonTracker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monitor", type=int, default=0)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--head", choices=HEADS, default="pumpkin_head")
    parser.add_argument("--cue", choices=tuple(LIVE_CUES), default="witch_flyby")
    args = parser.parse_args()
    config = Config(
        demo_mode=True,
        projector_monitor=args.monitor,
        fullscreen=args.fullscreen,
        camera_width=640,
        camera_height=480,
    )
    renderer, camera = GpuProjector(config), DemoCamera(config)
    identities = PersonTracker()
    camera.start()
    renderer.start()
    last_sequence = -1
    ready = False
    started = time.monotonic()
    try:
        while time.monotonic() - started < args.seconds:
            for event in renderer.poll():
                print(json.dumps(event), flush=True)
                if event["type"] == "error":
                    raise RuntimeError(event["error"])
                if event["type"] == "stopped":
                    return
                if event["type"] == "ready":
                    ready = True
                    renderer.send("cue", name=args.cue)
            if not renderer.process.is_alive():
                raise RuntimeError("Renderer exited; check the preceding diagnostics")
            if not ready and time.monotonic() - started > 10:
                raise RuntimeError("GPU renderer startup timed out")
            frame = camera.latest()
            if frame and frame.sequence != last_sequence:
                people = identities.update(camera.people, frame.timestamp)
                renderer.mailbox.publish(
                    frame.color,
                    dict(
                        people=encode_people(people),
                        active_effects=[args.head],
                        effect_settings={"effect_intensity": 0.75},
                    ),
                )
                last_sequence = frame.sequence
            time.sleep(0.005)
    finally:
        camera.stop()
        renderer.stop()


if __name__ == "__main__":
    main()
