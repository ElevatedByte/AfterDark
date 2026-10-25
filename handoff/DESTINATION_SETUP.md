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


## Setup completion audit — 2026-10-24

Reviewed START_HERE.md against this workstation's existing installation and
verification records. The fresh local Python 3.11.17 environment and original
requirements were already installed; reinstalling or replacing the working
virtual environment was unnecessary. Re-ran `setup_project.py --check --dev`:
pinned dependencies, pip consistency, pytest/Ruff availability, and model SHA-256
all passed. Reverified all 144 manifest entries inside the retained original ZIP;
the developed working tree intentionally differs from the transfer snapshot.

Created the previously absent `.env` from `.env.example`, selecting monitor 0
and windowed output to match run-local.sh's existing defaults. Loopback binding,
real-camera mode, and all other example defaults are retained. The file is Git
ignored. Launchers load it on their next launch; direct Python launches do not.
Both Bash launchers passed syntax checks. No running show was restarted.

Current verification: 62 unit tests passed, Ruff passed, and all 17 isolated
synthetic smoke checks passed (SDL dummy; 16.2 synthetic FPS; 0.21 s shutdown).
One existing Starlette/AnyIO deprecation warning remains. Sandbox socket creation
was blocked and its unit-test run stalled after 12 tests; host-loopback reruns
passed and the stalled test process was stopped. Smoke output is in
`artifacts/smoke-test.json` and `artifacts/smoke-server.log`.

All applicable installation/rehearsal steps in START_HERE.md are complete.
Physical extended-projector routing, fullscreen on that projector, real-person
tracking, and optional audio still require hardware acceptance. The optional
user service is outside START_HERE.md and remains a template. GPU migration is
separate development work; this audit does not change the active CPU renderer.


## LAN controller access — 2026-10-24

The user explicitly authorized access from other devices on this network,
overriding the earlier loopback-only deployment requirement for this workstation.
`.env` now sets `HOST=0.0.0.0`; run-local.sh honors HOST with a loopback fallback.
The running single-worker server was restarted on all IPv4 interfaces at port
8000, retaining the desktop environment and stopped camera/projector state.
Current controller URL: http://192.168.0.198:8000 (eno1, 192.168.0.0/24).
This address is DHCP-assigned and can change; reserve it in the router if desired.

Verified HTTP 200 for the controller page and API status over the LAN address,
and WebSocket status delivery with the matching LAN browser Origin. Confirmed
listener 0.0.0.0:8000. Verification ran on this workstation; another physical
client and router client-isolation behavior have not been tested.
UFW configuration has ENABLED=no. Privileged `ufw status` requires interactive
sudo authentication, so live firewall rules were not fully inspected; no firewall
rules were changed. If another client is blocked by a separately enabled firewall,
allow TCP 8000 from 192.168.0.0/24 on eno1 rather than disabling that firewall.

The controller remains unauthenticated: devices that can reach port 8000 can
control the show and view previews. No router port forwarding or public hosting
was configured. To undo LAN access, set HOST=127.0.0.1 in .env and restart through
run-local.sh. Direct Python commands do not load .env; use the launcher for the
persistent setting. No user service was installed.


## Automatic boot startup enabled — 2026-10-24

At the user's request, installed deploy/afterdark.service as
`~/.config/systemd/user/afterdark.service`, enabled it for `default.target`, and
ran `loginctl enable-linger deven` (verified Linger=yes). This replaces the earlier
optional graphical-session template instructions: the website now starts at boot
without login and remains up after logout. The unit uses Restart=on-failure and
runs the local launcher with the existing LAN binding on port 8000. The previous
manual server was shut down cleanly before service takeover; one worker remains.

`.env` now has AUTO_START_CAMERA=false, matching the stopped state at takeover.
The website starts without requiring camera or desktop hardware. Start camera
and projector from the controller when needed. Projector output requires an
active graphical login; before-login website availability is separate from
physical projector acceptance. The current user manager already has the desktop
display environment. If session credentials change, import the current desktop
environment and restart the service from the logged-in desktop terminal.

Verified enabled/active state, a managed restart, LAN HTTP and WebSocket status
at http://192.168.0.198:8000, and a single 0.0.0.0:8000 listener. No reboot was
performed; boot behavior is configured, not verified by a physical reboot.
No firewall or router settings were changed in this step.

Manage from this user's terminal:

```bash
systemctl --user status afterdark
systemctl --user restart afterdark
journalctl --user -u afterdark -f
systemctl --user disable --now afterdark  # undo automatic app startup
```

Do not start a second manual copy while the service is active. Lingering is an
account-wide setting; disabling this service does not disable other user services.


## Persistent Ethernet address — 2026-10-24

User requested a stable address across reboots. Active NetworkManager profile
`afterdark-static` (ea47ca50-dcfa-47d2-af4f-7539c4650f6f) now uses manual IPv4
192.168.0.198/24, gateway/DNS 192.168.0.1, on eno1 / MAC 10:60:4B:5C:4F:96.
Autoconnect is enabled with priority 100. NetworkManager persisted it through
Netplan at /etc/netplan/90-NM-ea47ca50-dcfa-47d2-af4f-7539c4650f6f.yaml;
D-Bus Unsaved=false confirmed. The installer-managed profile retained auto method
when edited, so a dedicated profile was necessary. Original netplan-eno1 was
returned to DHCP with no manual address/gateway/DNS and retained as a lower-priority
fallback. Before-change profile details are in work/network-before-static.txt.

Activated the static profile successfully, verified unlimited address lifetime,
static default route, DNS resolution, and HTTP 200 at http://192.168.0.198:8000.
No reboot was performed. This supersedes the prior DHCP-address description.
The router's pool/reservations have not been inspected or changed. To prevent
the router leasing this address to a different client, reserve 192.168.0.198
for MAC 10:60:4B:5C:4F:96 or exclude that address from its DHCP pool. Host-side
static configuration alone cannot guarantee freedom from router lease conflicts.

Rollback from a local desktop terminal:
`nmcli connection modify afterdark-static connection.autoconnect no`
then `nmcli connection up netplan-eno1`.


## Automatic random visitors and effects — 2026-10-24

Implemented server-owned random scheduling in app/cues/automation.py and the
runtime frame loop. Every event gets a newly sampled uniform 3–10 second delay.
The selection includes all seven visitors plus lightning, bats, ghost appearance,
and spell burst. Immediate repeats and currently active visitors are excluded.
Reset/stop actions and sound-only scream are excluded. Delayed frames schedule
from the present time rather than accumulating a burst. Automatic events reuse
the existing bounded command queue and normal effect/audio handling; a full
manual queue takes priority. Works on standby without a camera or browser.

The website has an Automatic visitors & effects switch. Stop animations also
pauses automation; turn the switch on again to resume after a fresh delay.
Config RANDOM_SHOW defaults false for isolated tests/other installations;
this workstation's .env sets RANDOM_SHOW=true, enabling automation after boot.
Operator toggle state is in memory and returns to the configured default on
service restart, like the other runtime show controls. Interval is fixed at
3–10 seconds. Existing manual buttons and per-person effects are preserved.

Verification: 65 unit tests passed, including interval bounds, no catch-up burst,
repeat/active-cue exclusion, pause/resume, and stop-button behavior. Ruff passed.
Existing Starlette/AnyIO warning remains. The isolated SDL dummy smoke test
checks existing scenes, effects, cues, and controls; see artifacts/smoke-test.json.


## Saved preferences and Start/Stop show — 2026-10-24

Added prominent Start show and Stop show buttons above system status. Both use
the existing WebSocket dispatcher; equivalent HTTP endpoints are POST
/api/show/start and /api/show/stop. Start requests camera/projector and enables
random automation together. Stop clears the bounded pending-trigger queue,
disables automation, requests camera/projector shutdown, and resets transient
animations on the processing thread. Scene/effect selections and sliders remain.
The UI distinguishes starting, running, stopping, stopped, automation-only, and
manual operation, and displays hardware errors rather than claiming success
from a command acknowledgement. Existing individual controls remain available.

The local .env now sets SETTINGS_PATH to
/home/deven/Documents/Codex/Afterdark/work/show-settings.json. Settings changes,
scene selection, effect toggles, Stop animations, and Start/Stop show save a
versioned, validated JSON document using temporary-file replacement and fsync.
Saved preferences include scene, active effects, automation, effect sliders,
smoothing, maximum people, monitor, fullscreen, debug skeleton, and adaptive
resolution. Settings are shared across controllers and restored after restart;
this supersedes the earlier note that all operator settings are in memory.
Camera/projector requested/running state, person IDs/assignments, active visitors,
and telemetry are deliberately session state. The website still boots without
starting camera/projector; Start show opens them. Saving automation on/off takes
precedence over RANDOM_SHOW on subsequent launches. Start show enables it again.

The initial saved document was seeded from the live operator selections before
deployment. Startup validates the entire saved file before applying preferences.
Invalid/unreadable files leave defaults active and show a visible warning. Save
failures preserve the prior file and report that active changes were not saved;
a subsequent successful change clears the warning. No telemetry writes occur.
The file is under Git-ignored work/; include it separately when moving personal
preferences to another workstation. Config without SETTINGS_PATH retains the
previous in-memory behavior. Smoke tests remove inherited SETTINGS_PATH so they
cannot change live preferences.

Validation: 73 tests passed, Ruff and diff whitespace checks passed, and all 18
synthetic SDL-dummy smoke checks passed. Added coverage for restoration, excluding
runtime/person state, invalid files, atomic write failure/recovery, concurrent
controllers, a full trigger queue, and HTTP/WebSocket start/stop. Browser testing
on the LAN controller confirmed Start show brought up the real camera (connected)
and projector window on monitor 0 with automation enabled, with no runtime error.
Stop show shut down both and cleared visitors. A browser-changed automation
setting survived an actual systemd service restart. Physical extended-projector
routing and real-person acceptance were not repeated. Restored the prior idle
state: camera/projector stopped and random automation enabled. Screenshot:
artifacts/saved-show-controls.png. One existing Starlette/AnyIO warning remains.


## Configurable random timing and selection — 2026-10-24

Added minimum/maximum delay controls (1–300 seconds) and separate Visitors/Effects
checkbox groups in Live cues. Apply timing saves the pair together; checkboxes,
Select all, and Clear save immediately. Defaults remain 3–10 seconds and all seven
visitors plus lightning, bats, ghost appearance, and magic burst. These are the
existing triggered effects; person-attached effect assignments remain separate.

SettingsPatch and saved preferences now include random_min_seconds,
random_max_seconds, and random_triggers. HTTP/WebSocket reject unknown items,
nonfinite/out-of-range delays, and a minimum greater than the effective maximum,
including partial updates. Selection is normalized and deduplicated. Older saved
files load the original defaults for the new fields without losing other choices.
The timing pair in a saved file is validated before any saved setting is applied.

The server scheduler resets its pending delay when timing/selection changes.
Equal bounds give a fixed interval. Empty selection schedules nothing; Start show
does not overwrite the selection. A single selected item can repeat; a visitor
already playing finishes instead of restarting. If every selected visitor is
currently playing, that opportunity is skipped. No catch-up bursts are queued.
The queue admission check also rejects an event removed by a concurrent settings
change. Manual cue buttons continue to work regardless of automatic selection.

Validation: 79 tests passed, all 18 isolated SDL-dummy smoke checks passed, Ruff
and diff whitespace checks passed. Browser verified Apply timing, Clear, individual
visitor/effect choices, and live status updates. A 2–4 second range with only Witch
flyby and Magic burst survived an actual service restart; live event observations
confirmed only those selected items fired. Restored the user's original range
(3–10 seconds), all 11 items, and original automation state after verification.
Screenshot: artifacts/automation-options.png. No physical projector acceptance
was repeated. Existing Starlette/AnyIO warning remains.


UI layout update: moved the complete automatic visitors/effects settings block
(toggle, timing, and selection checklist) below the Animated visitors group and
its help text. This is an HTML ordering change; existing controls and saved
settings are unchanged. Static HTML is served directly; no service restart needed.


UI layout update: automation settings beneath the visitors now use a native
HTML details/summary disclosure labeled Automation settings, collapsed by default.
Click or keyboard activation expands the toggle, timing, and inclusion controls.
Collapsing the section does not change automation or saved show preferences.


Maximum people default changed to 8 in Config, .env, .env.example, and initial
controller markup. Applied max_people=8 to the running show through /api/settings
and verified it in work/show-settings.json for future restarts. No service
restart was needed. This changes capacity, not verified eight-person performance.
