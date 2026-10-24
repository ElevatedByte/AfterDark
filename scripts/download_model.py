"""Explicit setup step only: download the versioned official MediaPipe lite model."""

import argparse
import hashlib
from pathlib import Path
import urllib.request

URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
DEFAULT = (
    Path(__file__).resolve().parents[1] / "app/assets/models/pose_landmarker_lite.task"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    if args.output.is_file():
        print(f"Model already installed: {args.output}")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        URL, headers={"User-Agent": "HalloweenDisplay-Setup/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if len(data) < 1_000_000:
        raise RuntimeError("Downloaded model is unexpectedly small")
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError("Model checksum mismatch")
    temp = args.output.with_suffix(".download")
    temp.write_bytes(data)
    temp.replace(args.output)
    print(
        f"Installed {args.output} ({len(data)} bytes, sha256={hashlib.sha256(data).hexdigest()})"
    )


if __name__ == "__main__":
    main()
