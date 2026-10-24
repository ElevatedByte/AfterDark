# Project context

## Identity and intent

**Afterdark / Halloween Dance Display / Halloween Projector** is a local,
interactive Halloween show: a webcam sees people dancing, pose tracking follows
them, effects attach to their bodies or move through the scene, and an independent
window sends the composition to a projector. A browser controls the show.

The original source directory was
`/home/kitchen/ai-projects/interactive-halloween`. The chat workspace named
`Halloween Projector` did not contain the application. This package was copied
from the actual source directory on 2026-10-24. The source has no `.git` directory;
`source-snapshot.json` records the copied files and hashes instead of a commit.

The destination OS is **Linux**. Distribution, CPU architecture, GPU, drivers,
camera, and projector configuration still need detection on the new computer.
The user intends to do the GPU/control-plane changes there. No migration has been
implemented during packaging.

## Existing behavior to preserve

- Webcam capture on its own thread; reconnect/retry and stale-frame removal.
- MediaPipe multi-person pose/segmentation using its explicit **CPU** delegate.
- Stable internal IDs, smoothing, track retention, normalized landmarks/masks,
  gesture recognition and per-person cooldowns.
- Five scenes: Normal Camera, Pumpkin Dance, Skeleton Dance, Ghost Mode, Magic Mode.
- Ten effects: Pumpkin Head, Witch, Frankenstein, Vampire, Mummy, Skeleton, Bats,
  Ghost Trail, Magic Particles, Lightning.
- Seven visitor cues: witch flyby, ghost parade, spider drop, skeleton peek,
  pumpkin roll, black cat, zombie hands. Cues overlap, restart, expire, and cancel.
- Normal Camera gives each new tracked person one random person-attached effect.
  Themed scenes supply defaults; operator per-person overrides remain supported.
- Manual triggers, camera/projector start/stop, monitor/fullscreen controls,
  sliders, scene/tracking reset, debug skeleton, and optional audio cues.
- Festive haunted-house standby screen; visual cues work with camera stopped.
- Local synthetic demo mode, local art/model, no cloud inference, no account or
  OpenAI API requirement in the runtime.

## Actual current architecture

```text
OpenCV/V4L2 camera thread -> latest BGR camera frame
                              |
                  Python processing thread in FastAPI process
                  CPU pose inference -> identities -> gestures
                  output-size viewport -> CPU effects/cues -> letterbox
                              |
                 final BGR frame in multiprocessing shared memory
                        |                         |
                 Pygame/SDL child           JPEG preview/snapshot
                 projector window          FastAPI -> browser

Browser HTTP/WebSocket -> validated command dispatcher -> locked AppState
```

The browser already serves as a controller; it is not the primary renderer.
The missing piece is a GPU rendering engine with suitable process independence.
The Pygame child currently presents an image that Python/NumPy/OpenCV have already
composited on the CPU. A separate display process is not proof of GPU rendering.

Camera/pose resolution is separate from graphics resolution. The video is fitted
to an output-sized viewport **before** effects draw, then letterboxed. Normalized
landmarks and masks remain aligned to that viewport. Some older README sentences
say composition happens at camera resolution; the code and the September 17
high-resolution section describe the current implementation.

Preview JPEGs are about 640 px wide at ~8 FPS. `/api/output.jpg` provides a
full-resolution still on demand. There is no frontend build step, package.json,
Node dependency, database, or container requirement.

## Code map

| File/directory | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI factory, lifecycle, CLI, single Uvicorn worker, shutdown |
| `app/config.py` | Validated environment config; project-relative asset paths |
| `app/runtime.py` | Capture/inference/effect orchestration, preview, projector control |
| `app/camera/` | V4L2 camera thread and synthetic demo source |
| `app/tracking/models.py` | Normalized tracking data and tracker interface |
| `app/tracking/pose_tracker.py` | MediaPipe CPU adapter |
| `app/tracking/person_tracker.py`, `gesture_detector.py` | Identities, smoothing, gestures |
| `app/effects/manager.py` | Effect lifecycles, ordering, per-person filtering, cues |
| `app/effects/`, `app/cues/` | CPU drawing, animations, particles, history, art fallbacks |
| `app/renderer/compositor.py`, `sprites.py` | Viewport/letterbox, standby, sprite loading |
| `app/renderer/projector.py` | Shared BGR buffer, SDL child process, events and sound |
| `app/state/app_state.py` | Settings validation, state locks, person overrides, cue queue |
| `app/api/control.py`, `routes.py`, `websocket.py` | Shared command semantics and transports |
| `app/static/` | Plain local operator website |
| `tests/` | Behavior, state/API, tracking, effects/cues, HD alignment regressions |

HTTP routes are prefixed `/api`: `GET /status`, `/preview.jpg`, `/preview.mjpg`,
`/output.jpg`; POST camera/projector start/stop, scenes, effect enable/disable,
triggers, settings, and person effects. `/ws` carries commands and state updates
roughly every 0.2 seconds. `/docs` exposes the generated API documentation.
Use the actual `Command`, `SettingsPatch`, and routes as the contract.

## Dependencies and assets

Runtime direct pins: FastAPI 0.115.12, Uvicorn 0.34.2, websockets 15.0.1,
NumPy 2.2.6, opencv-contrib-python 4.11.0.86, MediaPipe 0.10.32,
pygame-ce 2.5.7. Dev pins add pytest 8.3.5, httpx 0.28.1, Ruff 0.11.13.
Requirements are authoritative; the observed source environment is recorded
separately for diagnostics, not as a universal cross-platform lockfile.

The included model is `app/assets/models/pose_landmarker_lite.task`.
SHA-256: `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`.
The official versioned download URL and expected digest are in
`scripts/download_model.py`. The baseline Git ignore excludes this model, but this
ZIP explicitly includes it. Preserve it when making future transfer archives.

Artwork includes the standby background and four transparent 1536×1024 atlases.
Their generation prompts and programmatic fallback art are retained. See
`app/assets/README.md`. No WAV/OGG cue recordings exist; missing sounds are
intentionally silent. `artifacts/pose-reference.jpg` is a historical inference
reference from Google's MediaPipe example assets, not a required runtime image.

## State and historical evidence

Operator changes are in memory. No live scene/settings or running service is
restored by extraction. `.env.example` is included; no `.env` existed at source.
The original README's `afterdark-display` service and hardcoded paths refer to
the old host and must be recreated from the destination's paths if desired.

`VERIFICATION.md` records historical hardware checks and 55 tests at the last
feature update. Its synthetic benchmarks are not a destination-machine promise.
The new transfer verification is recorded in `PACKAGE_VERIFICATION.md`.

Known limits: real multi-person show performance, two physical display routing,
Wayland placement, sound playback, ARM64, and the new GPU architecture require
destination testing. The existing low-FPS fallback can reduce camera processing
to 640×480; the configured output resolution stays independent. Preserve the
distinction between inference FPS, rendering FPS, preview FPS, and frame age.
