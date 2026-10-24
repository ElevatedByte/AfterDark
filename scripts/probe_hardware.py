"""Integration probe: real camera/model/SDL, no unit testing of native windows."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
from app.config import Config
from app.renderer.compositor import standby_frame, draw_debug
from app.renderer.projector import Projector
from app.tracking.pose_tracker import MediaPipePoseTracker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dummy-display", action="store_true")
    parser.add_argument("--seconds", type=float, default=10)
    args = parser.parse_args()
    if args.dummy_display:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    config = Config.from_env()
    if args.dummy_display:
        config = config.model_copy(update={"projector_monitor": 0})
    cap = cv2.VideoCapture(config.camera_index, cv2.CAP_V4L2)
    opened = cap.isOpened()
    ok, frame = cap.read() if opened else (False, None)
    cap.release()
    if not ok:
        frame = standby_frame(640, 480)
    result = {
        "camera_opened": opened,
        "camera_read": ok,
        "simulated_display": args.dummy_display,
    }
    try:
        tracker = MediaPipePoseTracker(config)
        people = tracker.detect(frame, 1)
        tracker.close()
        result.update(model_initialized=True, detected_people=len(people))
        draw_debug(frame, people)
    except Exception as exc:
        result.update(model_initialized=False, model_error=str(exc))
    projector = Projector(config)
    projector.shared.publish(frame)
    projector.start(config.fullscreen, config.projector_monitor)
    events = []
    try:
        until = time.monotonic() + args.seconds
        while time.monotonic() < until:
            events.extend(projector.poll())
            time.sleep(0.05)
        result["projector_events"] = events
        result["projector_launched"] = any(e.get("running") for e in events)
        result["projector_fullscreen"] = any(e.get("fullscreen") for e in events)
    finally:
        projector.stop()
    print(json.dumps(result, indent=2))
    Path("artifacts").mkdir(exist_ok=True)
    Path(
        "artifacts/hardware-" + ("dummy" if args.dummy_display else "real") + ".json"
    ).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
