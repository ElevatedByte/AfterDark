# Verification — 2026-09-09

## Passed

- **21 automated tests**: gestures and cooldowns; jump re-arming; landmark normalization/confidence; identity matching and dropout handling; smoothing; concurrent state changes; HTTP scene/effect/settings controls; WebSocket commands/errors; person overrides; effect lifecycle/decay/zero intensity; camera recovery after failed reads and native exceptions.
- **Python lint/format**: `ruff check` and `ruff format --check` passed. Python compilation and Bash syntax checks passed.
- **End-to-end smoke**: all five scenes, all six effect toggles, every manual cue, person assignments, maximum-people changes, WebSocket status/commands, final JPEG preview, projector fullscreen acknowledgement, projector restart, camera restart, tracking reset, scene reset, and shutdown with an active MJPEG preview.
- **Smoke performance**: 29.9 FPS with two **synthetic** dancers at 640×480. This is not a MediaPipe benchmark. Shutdown with a preview connected completed in 0.21 seconds.
- **Real webcam**: `/dev/video0` opened and returned a frame. The complete application then ran with `camera_connected=true`, `tracking_status=ready`, and no tracking/runtime error.
- **Real runtime sample**: 19.4 FPS at 640×480 after automatic fallback, about 23.9 ms measured frame age at composition. No person was visible/detected in that sampled live camera frame; this does not measure 2–4-person performance.
- **Real model positive inference**: the official MediaPipe pose reference photograph produced 1 person with 15 mapped landmarks and 1 segmentation mask. A side-by-side composite of two copies produced 2 people, each with 15 mapped landmarks and a separate mask. First-call timings were about 104 ms and 79 ms, respectively; these are warm-up/single-call measurements, not sustained FPS.
- **Real fullscreen window**: the Pygame child launched fullscreen on monitor 0 using the **X11** driver, with a configured 1920×1080 output. SDL reported a 2560×1440 desktop. The probe then closed the window.
- **Unavailable monitor handling**: default monitor 1 correctly produced a clear error while keeping the application available; this host exposes only one monitor.
- **Browser check**: dashboard loaded at `http://localhost:8000`, WebSocket connected, live composite preview displayed, Pumpkin Dance switched live, Bats toggled off, and two rehearsal participants were listed separately. The final real-camera dashboard also reported Connected / Tracking ready. Camera capture was stopped after verification.
- **Missing sounds**: manual sound cues without cue files did not crash the smoke runtime. No playback recording or audio device output was verified.

## Not verified on physical hardware

- Two physical displays/projector routing: only one monitor was connected.
- Tracking 2–4 moving children, crossing/occlusion behavior, actual jump/wave accuracy, and FPS under a full live show.
- Physical USB unplug/replug during operation (recovery has automated simulated failure coverage).
- Wayland-specific placement and fullscreen behavior, Raspberry Pi/ARM64, or depth cameras.
- Sound output with actual WAV/OGG assets.

## Environment and reproducibility

Python 3.11.15; dependencies pinned in `requirements.txt`. The pinned MediaPipe model is installed locally and its download checksum was verified. No cloud inference was used. The optional reference photograph was downloaded solely for validation from `https://storage.googleapis.com/mediapipe-assets/pose.jpg`; it is not used by the application or bundled as a runtime asset.

Native camera/display/audio access and loopback sockets were unavailable inside the restricted execution sandbox. Hardware probes and HTTP/WebSocket tests therefore ran in the host desktop environment. A sandbox-only MediaPipe import failed through its PortAudio dependency; the same model initialized correctly in the host session. The API test client also needed host socket access for its event loop. These were environment restrictions, not ignored test failures.

One test-library deprecation warning remains: Starlette's test client references an AnyIO alias scheduled for removal. It does not affect the tested application behavior.

Reports generated during this run:

- `artifacts/smoke-test.json`
- `artifacts/smoke-server.log`
- `artifacts/hardware-real.json`
- `artifacts/hardware-dummy.json`
- `artifacts/tracking-probe.json`
- `artifacts/real-runtime-status.json`

Repeat with:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check app scripts tests
.venv/bin/python scripts/smoke_test.py
PROJECTOR_MONITOR=0 .venv/bin/python scripts/probe_hardware.py --seconds 10
# Optional positive inference using your own local full-body reference image:
.venv/bin/python scripts/probe_tracking.py /path/to/reference.jpg
```

## Relocation verification — 2026-09-09

Moved the project to `/home/kitchen/ai-projects/interactive-halloween`. Stopped the previous app service and stale project test/probe processes first. Verified 61 project files against their pre-move hashes. Recreated `.venv` from cached packages at the new path; all 39 installed package versions were preserved, with no downloads.

The restarted `afterdark-display.service` uses the new directory for both `WorkingDirectory` and `ExecStart`. The old project directory is absent. The dashboard returns HTTP 200 at `http://localhost:8000`; camera and projector remain stopped as before the move.

All 21 tests and the complete isolated smoke test passed from the new directory. The smoke test included projector worker startup/restart, fullscreen acknowledgements, scene/effect controls, and connected-preview shutdown. The relocation run measured 29.9 synthetic FPS and 0.26-second shutdown.

## Mode-specific effect defaults — 2026-09-09

Random individual effects now apply only in Normal Camera mode. Themed modes supply the selected scene effects as the initial default for existing and newly detected people, including after tracking resets. Returning to Normal Camera assigns fresh random effects to retained tracks. Individual controls and API overrides remain available in every mode. Manual changes, No effects, and Follow scene persist across tracking updates and brief dropouts; only a subsequent scene selection or tracking reset clears them.

All 27 tests passed. The end-to-end smoke test passed all five scene transitions, new track defaults in each mode, individual-effect changes, No effects, and Follow scene in themed modes, return to random effects in Normal Camera, and camera/projector restart checks. The live user service was restarted and the prior scene, settings, and camera/projector requests restored.

## Additional character overlays — 2026-09-15

Added Witch, Frankenstein, Vampire, and Mummy, bringing the catalog to ten effects. All four use original programmatic BGRA artwork and the shared `HeadOverlay` renderer, with independent per-person smoothing, shoulder-based scale, nose anchoring, and expanded rotation bounds for hats, collars, and ears. Pumpkin Head now uses that same renderer. No new dependencies, models, or downloads are required.

The new characters appear in the effects rack and person selector, and join the random pool only in Normal Camera. The five scene defaults and editable per-person overrides in every mode are preserved. HTTP and WebSocket effect-list limits now follow the expanded catalog.

- All **38 tests passed**, including character lifecycle/intensity, smoothing and confidence dropouts, clipping and processing-resolution changes, four independent character assignments, scene defaults, and HTTP/WebSocket combinations. The previously documented AnyIO deprecation warning remains.
- `ruff check`, `ruff format --check`, and JavaScript syntax validation passed.
- The isolated smoke test passed all ten toggles, the four character assignments with live previews, all scene transitions, WebSockets, camera/projector restart, fullscreen acknowledgements using **SDL dummy**, and shutdown with a connected preview. Sample: 27.2 FPS with two synthetic dancers; this is not a webcam/inference benchmark.
- Visually reviewed the actual rendered artwork and face alignment in `artifacts/character-overlays.jpg`.
- Restarted `afterdark-display.service` from `/home/kitchen/ai-projects/interactive-halloween` and restored prior scene, effect settings, maximum people, monitor, and camera/projector requests. Both camera and projector were stopped before the update and remain stopped.
- Reloaded the existing dashboard at `http://localhost:8000`, confirmed its connected state and all four new controls, enabled each via the browser, observed four active effects, then restored all four to off.

These are 2D pose-driven head overlays requiring a visible nose and shoulders. Physical webcam/projector behavior was not re-probed for this feature; the hardware results and limitations above still apply. Live state snapshots are in `artifacts/character-update-before.json` and `artifacts/character-update-live.json`.

## Live cue animations — 2026-09-15

Added seven timed visitors: Graveyard peek (skeleton and gravestone), Witch flyby, Ghost parade, Pumpkin roll, Spider drop, Zombie hands, and Moonlit cat. Each plays over the final camera/standby composite without requiring a tracked person. Independent cue timelines permit overlap, restart on repeated clicks, and expire automatically. Stop animations cancels these visitors without modifying scene/person effect choices. Scene changes and tracking resets clear them. Original artwork is cached locally; no new dependencies or downloads were needed.

- **48 tests passed**, including cue movement, expiration/retrigger, zero intensity, concurrent playback, resolution changes (including portrait frames), cancellation, runtime status, scene/tracking reset, HTTP and WebSocket control, and all existing tracking/effect tests. The previously documented AnyIO deprecation warning remains.
- Ruff lint and formatting and JavaScript syntax validation passed.
- The full isolated smoke test passed: seven visitors concurrently active, preview output, natural completion, cancellation, playback while the camera is stopped, all existing scenes/character effects, WebSockets, projector restart/fullscreen with SDL dummy, and shutdown with a connected preview. Final synthetic sample: 29.8 FPS; shutdown: 0.21 seconds. This sample is not a benchmark of physical pose tracking or seven-cue rendering throughput.
- Rendered and visually inspected `artifacts/live-cues-preview.jpg`; exported a six-second reel at `artifacts/live-cues-preview.mp4` using the actual timelines. `scripts/render_cue_previews.py` regenerates both locally. Refined the cat glow/motion and removed a ghost silhouette seam during QA.
- Restarted the user service from `/home/kitchen/ai-projects/interactive-halloween`, restored the previous scene/settings and camera/projector requests, and verified its new cue catalog. The camera and projector were stopped before and after the update.
- Browser verification at `http://localhost:8000`: all seven buttons are visible in Live cues → Animated visitors; clicked every button, observed **7 PLAYING** and animated preview output; verified restarting cues and Stop animations returning the shelf to **READY**. Fixed stale cached CSS with versioned dashboard asset URLs and visually verified the final button grid. Left the working dashboard tab available.

Physical webcam/projector access was not re-probed for this feature; the earlier hardware limitations still apply. These are original 2D overlays, and cue timings are approximately five to six seconds. Live state snapshots are in `artifacts/live-cues-before.json` and `artifacts/live-cues-after.json`.

## Festive waiting screen — 2026-09-17

Replaced the plain standby screen with a generated haunted-house illustration, glowing pumpkins, moonlight, and the exact title “The Dance Floor Awaits”. The built-in image generation tool produced the 1672×941 PNG, saved directly to `app/assets/backgrounds/haunted-house-standby.png`; its exact prompt is saved alongside it. Runtime uses only that bundled local asset and adds no dependencies or network access.

The compositor caches image loading and up to three prepared resolutions, returns isolated frame copies for cue rendering, supports 16:9/4:3 center crops with the title intact, and fits unusual aspect ratios without cropping the title. Camera reconnection preserves the illustration with a small status caption. Missing or unreadable artwork falls back to a text screen.

All 48 existing tests, Ruff checks, and the full isolated smoke test passed. Additional direct checks covered 1280×720, 640×480, 1920×1080, portrait fitting, cache copy isolation, missing-image fallback, reconnect captions, and a witch cue over the illustration. Visually reviewed the 4:3/reconnection renders and the actual served JPEG. Smoke fullscreen checks used SDL dummy; physical hardware was not re-probed.

Restarted `afterdark-display.service` from the project directory and restored prior scene, settings, and camera/projector requests. Camera and projector remain stopped. Reloaded the dashboard to reconnect its preview stream after restart and visually confirmed the new illustration and title in the live preview. Captures and state snapshots are saved as `artifacts/haunted-house-*.jpg` and `artifacts/standby-update-{before,after}.json`.


## High-resolution overlays — 2026-09-17

Upgraded all five head characters, the skeleton skull, bat particles, ghost apparition and all seven live visitor animations with locally bundled, detailed storybook sprites. Four transparent 1536×1024 atlases are in `app/assets/overlays/`; the original generated files are preserved and the exact built-in generation/editing prompts are saved alongside them. The cat blink was generated as a matching edit to preserve its pose. Original programmatic artwork remains as a fallback for missing/unreadable packs. No runtime packages, cloud services or network dependencies were added.

Composition now fits the camera into an output-resolution viewport before drawing effects/debug graphics, then adds aspect-preserving bars. Shared memory is sized for the projector output. Camera/pose resolution and normalized segmentation coordinates remain separate from graphics resolution. Magic uses soft additive star glows, bats use cached flapping/rotated sprites, skeleton bones have shading, and lightning has scaled glow strokes and branches. Ghost histories are pre-tinted float32 buffers capped at eight frames and 480×270; only their difference is blended onto the full-resolution foreground. Bar filling avoids redundant full-frame writes.

- **55 tests passed**, including new coverage for 640×480/1280×720 capture into 1080p/4K/portrait output, landmark alignment, initialized letterbox bars, input immutability, output-sized shared memory, native JPEG snapshots, asset transparency/fallbacks, and bounded 4K ghost processing. Existing scene defaults, random assignment and per-person overrides passed unchanged. The existing AnyIO test-library deprecation warning remains.
- Ruff lint and formatting checks and JavaScript syntax validation passed.
- The isolated end-to-end smoke test passed all 16 checks, including native output JPEG dimensions independent of capture, every scene/effect/visitor, editable per-person defaults, HTTP/WebSocket control, camera/projector restart, fullscreen acknowledgements using **SDL dummy**, and shutdown with a connected preview. Final sample: 23.7 synthetic FPS; shutdown: 0.16 seconds. This is not a real camera/inference benchmark.
- A serialized synthetic 640×480 → 1920×1080 composition benchmark with four poses measured median / p95: four individually assigned characters **9.97 / 11.68 ms**; skeletons **16.48 / 18.22 ms**; ghost trails **26.57 / 32.15 ms**; magic/bats **16.83 / 43.51 ms**. Enabling all ten effects on all four people plus all seven visitors is a stress case: **113.49 / 119.71 ms**, below 30 FPS. These numbers exclude capture, inference, JPEG encoding and native display work; they are not a promised end-to-end frame rate. Reproduce with `scripts/render_hd_previews.py`; raw results are in `artifacts/hd-render-performance.json`.
- Visually inspected actual renders of all characters and visitors, their transparent edges, head placement and the matching cat blink. Full-size frames are in `artifacts/hd/`; overview images are `artifacts/hd-overlays-preview.jpg` and `artifacts/live-cues-preview.jpg`. The animation reel was regenerated at `artifacts/live-cues-preview.mp4`.
- Restarted `afterdark-display.service` with its WorkingDirectory and run.sh under `/home/kitchen/ai-projects/interactive-halloween`. Restored Normal Camera, empty global effects, all prior sliders, max people 6, monitor 1, fullscreen preference and camera/projector requests. Camera/projector were stopped before and remain stopped. State snapshots are `artifacts/hd-update-before.json` and `artifacts/hd-update-after.json`.
- Reloaded the live controller at `http://localhost:8000`, confirmed Controller connected, triggered the new artwork through the existing visitor buttons, and captured actual service output with skeleton, witch and cat at 1920×1080 (`artifacts/hd-live-visitors.jpg`). Stopped verification cues afterward. Verified the new **Full-size frame** link opens a 1920×1080 still and Back returns to the connected controller. The small MJPEG preview remains 640 pixels wide; full-size JPEG is encoded only on request via `/api/output.jpg`.

Physical webcam and projector hardware were not re-probed for this visual update; earlier hardware limitations still apply. Sprite source detail suits normal 1080p character sizes, but very large heads or 4K closeups still upscale individual artwork. RGB camera detail remains limited by capture resolution. Heavy simultaneous effects can reduce FPS; ghost echoes are intentionally soft. All project changes and bundled assets are in the actual project directory, not `/tmp`.
