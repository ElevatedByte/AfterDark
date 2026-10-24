"""Verify the extracted transfer snapshot before editing it (standard library only)."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = ROOT / "handoff/SHA256SUMS.json"
    if not manifest.is_file():
        print("Missing handoff/SHA256SUMS.json; restore the original transfer ZIP.")
        return 1
    files = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    failures = []
    for relative, expected in files.items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT):
            failures.append(f"Invalid manifest path: {relative}")
        elif not path.is_file():
            failures.append(f"Missing: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(f"Changed or corrupt: {relative}")
    if failures:
        print("\n".join(failures))
        print(
            "Edits after extraction also change hashes; compare with the original ZIP."
        )
        return 1
    print(f"Verified {len(files)} files: source, assets, model, and handoff documents.")
    print("The manifest itself is not signed; this is an integrity check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
