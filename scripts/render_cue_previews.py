"""Export a local contact sheet and short video of the actual cue timelines."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import cv2
    import numpy as np
    from app.cues.animations import create_cues
    from app.cues.catalog import LIVE_CUES

    cues = create_cues()
    for cue in cues.values():
        cue.settings = {"effect_intensity": 1.0}
        cue.trigger()
    width, height = 426, 270
    target = ROOT / "artifacts"
    target.mkdir(exist_ok=True)
    video = cv2.VideoWriter(
        str(target / "live-cues-preview.mp4"),
        cv2.VideoWriter_fourcc(*"mp4v"),
        15,
        (width * 3, (height + 36) * 3),
    )
    if not video.isOpened():
        raise RuntimeError("OpenCV could not open the MP4 preview writer")
    try:
        for step in range(90):
            sheet = np.full(((height + 36) * 3, width * 3, 3), (26, 21, 27), np.uint8)
            for i, (name, cue) in enumerate(cues.items()):
                frame = np.full((height, width, 3), (41, 32, 39), np.uint8)
                cv2.rectangle(frame, (0, 222), (width, height), (51, 43, 45), -1)
                cv2.line(frame, (0, 222), (width, 222), (68, 57, 62), 1)
                cue.update(frame, [], cue.duration / 90)
                cue.render(frame)
                x, y = (i % 3) * width, (i // 3) * (height + 36)
                sheet[y + 36 : y + 36 + height, x : x + width] = frame
                cv2.putText(
                    sheet,
                    LIVE_CUES[name]["label"],
                    (x + 14, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (202, 224, 251),
                    1,
                    cv2.LINE_AA,
                )
            cv2.putText(
                sheet,
                "AFTERDARK / LIVE CUES",
                (width + 35, 740),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68,
                (202, 224, 251),
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                sheet,
                "Seven original animated visitors",
                (width + 35, 778),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (163, 164, 173),
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                sheet,
                "Actual renderer / normalized timelines",
                (width + 35, 808),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.43,
                (163, 164, 173),
                1,
                cv2.LINE_AA,
            )
            if step == 44:
                cv2.imwrite(str(target / "live-cues-preview.jpg"), sheet)
            video.write(sheet)
    finally:
        video.release()
    print(target / "live-cues-preview.jpg")
    print(target / "live-cues-preview.mp4")


if __name__ == "__main__":
    main()
