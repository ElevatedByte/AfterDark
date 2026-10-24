"""Optional positive-inference probe using a local full-body test photograph."""

import argparse
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.tracking.pose_tracker import MediaPipePoseTracker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    frame = cv2.imread(str(args.image))
    if frame is None:
        raise SystemExit("Image could not be loaded")
    report = {}
    for name, image in [
        ("single", frame),
        ("two_copies", np.concatenate([frame, frame], axis=1)),
    ]:
        tracker = MediaPipePoseTracker(Config(max_people=4))
        try:
            started = time.monotonic()
            people = tracker.detect(image, 1)
            report[name] = dict(
                people=len(people),
                masks=sum(p.segmentation_mask is not None for p in people),
                landmarks=[len(p.landmarks) for p in people],
                first_inference_ms=round((time.monotonic() - started) * 1000, 1),
            )
            assert people, "No pose detected in the supplied reference image"
            assert all(p.head and p.segmentation_mask is not None for p in people)
        finally:
            tracker.close()
    target = Path(__file__).resolve().parents[1] / "artifacts/tracking-probe.json"
    target.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
