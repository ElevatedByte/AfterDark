# Setup on the destination Linux computer

## Detect first

Check distribution/release, CPU architecture, Python versions, GPU model and
driver, graphical session (X11/Wayland), available camera devices, monitor layout,
and permissions. Keep the process in the logged-in user's desktop session.
Do not assume that the old machine's monitor 1, `/dev/video0`, Python path, or
`afterdark-display` user service will exist.

Python **3.11** is the baseline tested at source. The helper also allows 3.12,
but destination wheel availability must be verified. Avoid silently selecting a
newer system Python for these pins. The helper creates `.venv` with the interpreter
used to launch it; Python itself must already be installed. On Debian/Ubuntu,
ensure the matching Python venv package is present. The package does not include
an OS installer or GPU drivers.

## Native libraries

The original Linux prerequisites identify OpenGL runtime libraries, GLib,
PortAudio, SDL2, and an operational webcam/display session. On Debian/Ubuntu the
starting package set is below; resolve exact names for the detected release:

```bash
sudo apt update
sudo apt install python3-venv python3-pip libgl1 libglib2.0-0 libportaudio2 libsdl2-2.0-0
```

Install Python 3.11 and its matching venv package through the distribution or a
trusted Python installer if they are not already available. `python3-venv` may
correspond to a different system Python. Optional diagnostics include `v4l-utils`
and `x11-xserver-utils`. Fedora uses different package names; consult its package
manager rather than running Debian commands there. GPU-specific SDKs and a native
compiler should be selected after inspecting the GPU migration requirements.

## Environment and packages

```bash
python3.11 setup_project.py --dev
python3.11 setup_project.py --check --dev
```

The helper installs from the original requirements using pip. Transitive packages
are resolved on the destination, so this is not a hash-locked or fully hermetic
installer. `source-environment.txt` records the original installed versions for
comparison, not a replacement for the requirements. Keep any compatibility changes
explicit and tested. A missing wheel should produce a useful explanation rather
than an unreviewed dependency upgrade or a long accidental native build.

Use only **opencv-contrib-python** for the baseline. Do not also install
opencv-python or either headless variant, which share the `cv2` namespace. The
`pygame` import comes from **pygame-ce**, not a second `pygame` distribution.
MediaPipe imports audio support even for pose tasks; native PortAudio or desktop
audio/session restrictions can fail initialization. A successful pip install or
demo test does not validate MediaPipe initialization.

For an offline destination, obtain wheels for its exact OS/architecture/Python on
a compatible connected machine first, then use
`python3.11 setup_project.py --dev --wheelhouse /path/to/wheels`. The ZIP does not
contain those wheels. Its included model is verified even with `--wheelhouse`.

## Hardware and process behavior

- Camera capture in `app/camera/camera_manager.py` and the hardware probe use
  `cv2.CAP_V4L2`. This matches the requested Linux destination. Camera permissions,
  USB format negotiation, MJPEG support, and device index need local verification.
- This is a graphical application. A headless container or remote cloud session
  is not equivalent to access to the physical webcam and projector.
- Default binding is `127.0.0.1:8000`. Keep it loopback: there is no remote login or
  authentication, and origin checks alone are not authentication.
- One app process/one Uvicorn worker owns camera/tracking/state. Do not use multiple
  server workers or two app copies sharing the same camera and port.
- Camera/display calls can be blocked by execution sandboxes. Distinguish access
  restrictions from application failures. API tests can also need loopback socket
  access for their event loop; do not leave a hung test process running.
- `SDL_VIDEODRIVER=dummy` is for tests only. Remove it before a physical show.
  X11 and Wayland display routing differ; test actual extended-display placement.
- The old background user service is not exported. After interactive setup works,
  create a new user-session service with the new working directory and graphical
  session environment. Do not run the show as root or blindly copy old paths.
- A compiled renderer that opens a window still needs the user's graphical
  session. A system daemon without display access will not meet the projector goal.

## If the destination changes later

The added installer uses portable Python paths, but Windows/macOS application
support has not been established. Real capture needs a platform backend adapter;
`run.sh` and systemd instructions are Linux-oriented. A successful synthetic demo
does not establish native camera support. Choose the target GPU backend and
service model based on the actual platform rather than treating this snapshot
as an already portable native application.

## Before changing code

Run `python3 scripts/verify_transfer.py` once after extraction. It hashes all
manifest-listed files, including source, art, model and handoff documents. It
does not require third-party packages. Newly generated `.venv`, caches, and
unlisted files are ignored. The manifest is an integrity aid, not a signature.
Changes to listed files after development begins are expected to fail this
original snapshot check; retain the ZIP for comparison/rollback.
