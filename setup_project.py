"""Install the portable baseline into a new, local virtual environment."""

import argparse
import hashlib
from pathlib import Path
import platform
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
ENV = ROOT / ".venv"
PYTHON = ENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def run(*arguments):
    subprocess.run([str(a) for a in arguments], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dev", action="store_true", help="Also install test/lint tools"
    )
    parser.add_argument(
        "--check", action="store_true", help="Verify only; no installation"
    )
    parser.add_argument(
        "--wheelhouse",
        type=Path,
        help="Install offline from an existing wheel directory",
    )
    args = parser.parse_args()
    if sys.version_info[:2] not in {(3, 11), (3, 12)}:
        parser.error("Use Python 3.11 (tested) or 3.12 for this baseline.")
    if args.check and args.wheelhouse:
        parser.error("--wheelhouse only applies to installation")
    print(
        f"Host: {platform.system()} {platform.machine()}, Python {platform.python_version()}",
        flush=True,
    )
    if sys.platform != "linux":
        print(
            "Portability note: demo mode can be tried, but real camera capture currently "
            "requires a platform adapter; the source uses Linux V4L2.",
            flush=True,
        )
    if not PYTHON.is_file():
        if args.check:
            parser.error("No local .venv. Run setup_project.py --dev first.")
        if ENV.exists():
            parser.error("An incomplete .venv exists. Rename it and rerun setup.")
        venv.EnvBuilder(with_pip=True).create(ENV)
    run(
        PYTHON,
        "-c",
        "import sys; assert sys.version_info[:2] in {(3,11),(3,12)}, "
        "'Existing .venv has an unsupported Python; recreate it with Python 3.11'",
    )
    if not args.check:
        command = [PYTHON, "-m", "pip", "install"]
        if args.wheelhouse:
            wheelhouse = args.wheelhouse.resolve()
            if not wheelhouse.is_dir():
                parser.error("The wheelhouse directory does not exist")
            command += ["--no-index", "--find-links", wheelhouse]
        requirements = "requirements-dev.txt" if args.dev else "requirements.txt"
        run(*command, "-r", ROOT / requirements)
    run(PYTHON, ROOT / "scripts/check_dependencies.py")
    run(PYTHON, "-m", "pip", "check")
    if args.dev:
        run(PYTHON, "-m", "pytest", "--version")
        run(PYTHON, "-m", "ruff", "--version")

    from scripts.download_model import DEFAULT, SHA256

    if not DEFAULT.is_file():
        if args.check or args.wheelhouse:
            parser.error("Bundled pose model is missing. Restore it from the ZIP.")
        run(PYTHON, ROOT / "scripts/download_model.py")
    if hashlib.sha256(DEFAULT.read_bytes()).hexdigest() != SHA256:
        parser.error("Pose model checksum mismatch. Restore it from the ZIP.")
    print("Pinned runtime packages and bundled model verified.")
    print("This does not verify native libraries, camera, display, or GPU access.")
    print(
        "Read START_HERE.md for demo/run commands. No show or system service was started."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        print(
            "See the preceding error and handoff/PORTABILITY.md. "
            "Do not silently change the pinned dependencies.",
            file=sys.stderr,
        )
        sys.exit(1)
