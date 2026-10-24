# Afterdark on this workstation — 2026-10-24

Project root: `/home/deven/Documents/Codex/Afterdark`.
This is a local/offline Python application. Nothing from this migration was
published. The previously registered cloud Site still contains the transfer
snapshot; it is not the runtime and is not used by the projector.

## Installed baseline

Python 3.11.17 is local under `work/python/`, installed using uv 0.13.5.
`.venv/` was created from that interpreter. All original requirements are intact.
Optional GPU dependencies are separate in `requirements-gpu.txt`: ModernGL 5.12.0
and glcontext 3.1.0. No compiler, system package, GPU driver, camera configuration,
or system service was installed or changed. Native imports and MediaPipe model
initialization worked with the available libraries and wheels.

The transfer manifest verified all 144 files before source changes. The original
ZIP and its adjacent digest have also been retained in `work/baseline/`, so
removing the USB will not remove the rollback copy. The model and artwork remain
bundled. `work/installed-dependencies.txt` records resolved packages; this is an
environment snapshot, not a portable hash lockfile.

## Start and stop

Run in a terminal in the logged-in graphical session:

```bash
cd /home/deven/Documents/Codex/Afterdark
./run-local.sh --demo
```

Open `http://127.0.0.1:8000`. This rehearsal uses synthetic dancers and the full
CPU show. The output window starts only when **Start projector** is clicked.
The launcher enforces loopback binding, defaults to monitor 0/windowed output,
loads an optional trusted `.env`, and never installs or downloads anything.
Stop with Ctrl+C. Run one copy / one Uvicorn worker only.

For a real camera after connecting and checking it:

```bash
PROJECTOR_MONITOR=0 FULLSCREEN=false ./run-local.sh
```

Choose the actual extended projector display in the controller before fullscreen.
Do not assume the old computer's monitor 1. Remove `SDL_VIDEODRIVER=dummy` from
any test shell before physical use. The camera adapter remains Linux V4L2.

## Verification

```bash
.venv/bin/python setup_project.py --check --dev
.venv/bin/python -m pytest
.venv/bin/python scripts/smoke_test.py
.venv/bin/python scripts/probe_tracking.py artifacts/pose-reference.jpg
.venv/bin/python scripts/benchmark_runtime.py --seconds 10
```

The smoke script creates and stops its own server on an ephemeral loopback port.
The full suite currently has 62 tests; the smoke script has 17 checks, including
controller WebSocket disconnect/reconnect while output stays running. These are
synthetic/headless checks, not proof of physical webcam, NVIDIA, or projector use.
GPU tests use optional EGL; they explicitly permit software rendering only for
shader correctness tests and skip when EGL is unavailable.

## Updated hardware validation after connecting the USB camera

Host-level execution became available later in this session. The Galyimage Live
USB camera (Image+, eba4:1303) opened at `/dev/video0` and captured 30 frames at
1280x720. MediaPipe initialized; the sampled image had zero detected people, so
real-person tracking remains unverified. No camera images were saved.

Host `nvidia-smi` confirmed GTX 745 / driver 580.178.04. `xrandr` confirmed one
active HDMI display at 3440x1440. The projector is not connected yet.

The experimental head/cue renderer successfully opened a window on the NVIDIA
GTX 745, reported hardware OpenGL 3.3, composed the synthetic input, and shut down
cleanly. A portability fix now obtains OpenGL function pointers from the owning
SDL runtime; it needs no development-only `libGL.so` symlink. The standalone
rehearsal still does not constitute full-show or physical projector acceptance.
The full controller continues to use CPU composition.

The entries below record the earlier sandbox-only probe and are retained to
explain the difference between execution scopes. They do not override the
successful host checks above.

## Initial sandbox-only host and access limits

- Ubuntu 26.04.1 LTS, kernel 7.0.0-38-generic, x86-64.
- Intel Xeon E5-2670, 8 cores / 16 logical CPUs.
- PCI NVIDIA GeForce GTX 745 (GM107), attached to kernel driver `nvidia`.
- PCI Quadro K600 (GK107GL), with no active kernel driver listed for that card.
- NVIDIA kernel module reports 580.178.04. `nvidia-smi` cannot communicate with
  the driver from this execution environment; that alone does not establish a
  broken driver on the host desktop.
- Session environment reports Wayland, `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0`.
  DRM sysfs reports one enabled HDMI connector; DVI and VGA are disconnected.
  HDMI advertises 3440x1440 and other modes; this is not a verified active desktop
  resolution or a physical projector identification.
- No camera is enumerated in `/sys/class/video4linux` or exposed as `/dev/video*`.
- GPU device nodes are not exposed here. `xrandr` cannot open the display.
  Native OpenGL rehearsal exits during GLX context creation with `BadValue`.
  EGL works only through Mesa llvmpipe software OpenGL 4.5.
- No gcc/g++, CMake, Rust, Cargo, or Python 3.11 was initially on PATH. System
  Python is 3.14, deliberately not used for the pinned baseline.

Host-level read-only diagnostics were rejected by the execution approval policy,
which disables sandbox escalation. No attempt was made to bypass that restriction.
Use a normal desktop terminal for physical validation. If Codex continues to lack
device access, open this folder as a local Codex project with access to the user
session, or run the following probes in the workstation's desktop terminal:

```bash
nvidia-smi
xrandr --listmonitors
ls -l /dev/dri /dev/video*
# May need the distribution's mesa-utils diagnostic package:
glxinfo -B
```

Do not change drivers based only on sandbox failures. First establish whether the
normal terminal sees the NVIDIA renderer, camera, and intended projector.

## GPU migration stage delivered

The complete CPU renderer remains primary. `app/renderer/gpu.py` contains real
GLSL composition: source-size BGR camera upload, GPU viewport scaling/letterbox,
texture sampling, sprite transforms, and alpha blending. Five head characters
and all seven visitor cues reuse their original assets and animation timelines.
Shader correctness and a composed image were checked on software EGL.

`app/renderer/gpu_process.py` provides a separate renderer process owning SDL and
OpenGL, presenting its framebuffer directly to the window without full-resolution
CPU readback. It redraws independently of input publications and requires no
browser. A one-slot shared-memory camera/JSON mailbox has nonblocking publication,
an atomic sequence, timestamps, explicit stride/BGR8/sRGB contract, and a 64 KiB
metadata limit. Both control and event queues hold at most 32 items. Commands
carry protocol version and IDs, and emit acknowledgements. Health includes frame
age, sequence, stale input, active cues, and bounded timing samples. Input older
than one second switches to standby. Stop/restart and monitor selection are owned
by the process wrapper; fullscreen is a command or F key; Escape closes output.

Normal launches reject recognized software renderers. This is an experimental
head/cue rehearsal, not the migrated full show:

```bash
.venv/bin/python -m pip install -r requirements-gpu.txt  # setup only, online
.venv/bin/python scripts/gpu_rehearsal.py --monitor 0 --seconds 30
.venv/bin/python scripts/gpu_rehearsal.py --monitor 1 --fullscreen --head witch --cue spider_drop
```

CPU MediaPipe inference is unchanged. Skeleton rendering, particles/bats,
segmentation ghost history, lighting/lightning, debug drawing, sound integration,
live API/state bridging, GPU preview/snapshot transfer, device-loss recovery, and
physical monitor/fullscreen acceptance remain to be migrated or validated.
Unported effects explicitly fail in the experimental process rather than silently
vanishing. The original full show preserves them all through the CPU renderer.
The native window path passed a short hardware rehearsal on the current monitor
after host access became available. It is not enabled in the main controller. There is no claim of GPU speedup or 30 FPS acceptance yet.

OpenGL 3.3 + ModernGL is the first candidate because it reuses the existing SDL
window lifecycle and permits shader tests without a new native compiler. Vulkan
or a compiled Rust/C++ process would add a new toolchain and a larger migration
before the available backend is validated. This is a provisional stack choice,
not a claim that the installed NVIDIA/desktop combination supports the path.
ModernGL uses a compiled extension; this is not a standalone compiled executable.
Primary references consulted: [ModernGL context](https://moderngl.readthedocs.io/en/latest/reference/context.html),
[texture upload/readback](https://moderngl.readthedocs.io/en/latest/reference/texture.html),
and [pygame-ce display/OpenGL](https://pyga.me/docs/ref/display.html).

## CPU runtime improvements

Preview encoding now runs on a separate thread with one pending frame. A slow
encoder replaces stale pending frames rather than blocking processing. Small JPEG
previews and existing full-size snapshot endpoints retain their previous formats.
`renderer_backend`, `renderer_timings`, `preview_dropped`, and `preview_error`
are additive API status fields; the controller displays active CPU backend and
composition median/p95. Capture polling, capture read/prepare (real cameras), frame
copy, input age, inference, composition/control, shared publication, preview JPEG,
and SDL presentation have independent bounded timing windows. Demo inference
is only simulated pose selection. Frame age starts at the software frame timestamp;
it is not measured physical camera-to-photon latency.

## Remaining acceptance sequence

1. Validate hardware renderer, physical camera, extended projector, fullscreen,
   sound, and real tracking in the logged-in session.
2. Run the GPU rehearsal and collect hardware timings/GPU use. Validate context
   survival during fullscreen on the intended projector; only windowed host output
   has been tested so far.
3. Bridge live poses, assignments, scenes, triggers, and desired/actual state into
   the renderer protocol. Preserve existing HTTP/WebSocket semantics.
4. Port skeleton, particles, ghost masks/history, lighting and debug layers; use
   bounded mask buffers and GPU history. Add throttled GPU preview readback with
   no synchronous full-frame readback in normal presentation.
5. Test device loss, restarts, camera hotplug, slow/disconnected browsers, four
   real people, all effects/cues, sustained memory/latency, offline operation,
   and 1920x1080/30 FPS on the selected physical projector.
6. Make GPU rendering primary only after feature parity and physical acceptance.

## Optional user-session service

`deploy/afterdark.service` is a template only. It has not been installed/enabled.
It uses this folder, runs in the user session, binds loopback, defaults to windowed
monitor 0, and leaves the real camera stopped until requested. After manual
hardware acceptance, review settings and then run from the desktop terminal:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/afterdark.service ~/.config/systemd/user/
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XAUTHORITY XDG_RUNTIME_DIR
systemctl --user daemon-reload
systemctl --user start afterdark
journalctl --user -u afterdark -f
# Optional after verifying startup:
systemctl --user enable afterdark
# Stop / disable:
systemctl --user stop afterdark
systemctl --user disable afterdark
```

Do not run an interactive copy simultaneously. Graphical access and GPU permissions
must be available to the user service; a service name does not grant them.

## Rollback

The original local Git baseline tag is `transfer-baseline-20261024`, commit
`84a68d442817b23ea02b23cad40705e6786bf351`. Preserve current work before checking it
out. The model is excluded by the original Git ignore, so keep the bundled file.
For a completely clean recovery, extract the retained ZIP to a separate folder,
verify it with `scripts/verify_transfer.py`, and create a fresh Python 3.11 `.venv`
there. Do not overwrite the current working tree with an old archive.

To avoid experimental GPU code, simply use `./run-local.sh` (CPU default).
Optional ModernGL packages do not alter baseline direct pins. To restore a fully
baseline environment, create a new venv from the retained interpreter and install
only `requirements-dev.txt`.
