"""Render local storyboard previews for the three atmospheric visitor cues."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import cv2
    import numpy as np
    from app.cues.animations import create_cues
    from app.cues.catalog import LIVE_CUES
    from app.renderer.compositor import standby_frame

    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    background = standby_frame(960, 540, "The Dance Floor Awaits")
    rows = []
    for name in ("creeping_fog", "haunted_eyes", "ghost_portal"):
        cue = create_cues()[name]
        cue.settings = {"effect_intensity": 0.9}
        row = []
        for fraction in (0.30, 0.55, 0.80):
            cue.trigger()
            cue.update(background, [], cue.duration * fraction)
            frame = cue.render(background.copy())
            cv2.imwrite(str(output / f"{name}-{fraction:.2f}.png"), frame)
            row.append(cv2.resize(frame, (480, 270), interpolation=cv2.INTER_AREA))
        strip = np.concatenate(row, axis=1)
        label = np.full((42, strip.shape[1], 3), (24, 19, 25), np.uint8)
        cv2.putText(
            label,
            LIVE_CUES[name]["label"],
            (15, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (207, 222, 244),
            1,
            cv2.LINE_AA,
        )
        rows.append(np.concatenate((label, strip)))
    cv2.imwrite(str(output / "atmosphere-storyboard.png"), np.concatenate(rows))
    print(output / "atmosphere-storyboard.png")


if __name__ == "__main__":
    main()
