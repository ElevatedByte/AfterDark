"""Check exact direct dependency versions locally; no package index request."""

from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import sys

missing = []
for line in (
    (Path(__file__).resolve().parents[1] / "requirements.txt").read_text().splitlines()
):
    if not line or line.startswith("#"):
        continue
    name, expected = line.split("==")
    try:
        if version(name) != expected:
            missing.append(line)
    except PackageNotFoundError:
        missing.append(line)
if missing:
    print("Installing required packages: " + ", ".join(missing))
sys.exit(bool(missing))
