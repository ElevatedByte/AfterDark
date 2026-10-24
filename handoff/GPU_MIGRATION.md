# Requested next development: GPU renderer and browser control plane

## User requirements

1. The primary render engine should run on the GPU, potentially as a compiled
   service.
2. The website should be a control plane for graphics and effects.

Destination: Linux; GPU and distribution unknown. This document is a proposed
engineering direction and acceptance checklist, not a claim that the migration
exists. Language, GPU API, native framework, IPC and service manager remain open.

## Process boundaries

```text
Browser controller <-> local HTTP/WebSocket control API
                                      |
                         versioned commands / state / telemetry
                                      |
                    native GPU renderer and projector window
                                      ^
                     latest camera texture + pose/mask data
                                      |
                    camera/tracking producer (initially Python)

Renderer -> throttled small preview -> API -> browser
```

The rendering process owns GPU resources, frame timing, composition, and output
presentation. The browser controls it and displays telemetry/preview. Closing,
refreshing, or disconnecting the browser must not stop or throttle the show.
Keep the renderer runnable without an active browser. Decide whether capture and
tracking are in a companion process or eventually integrated into the native
engine; moving everything out of Python at once is not a requirement.

For Linux, a managed user-session process is a practical service boundary to
evaluate. A compiled executable is optional if measurements justify a different
GPU engine. Freezing Python into a binary, merely enabling GPU pose inference, or
uploading a finished CPU composition for display does not meet the graphics goal.

## Select a stack using this machine

Identify discrete/integrated GPU, driver, actual hardware renderer/backend,
supported API versions, Linux distribution, and deployment needs. Compare a small
number of native GPU approaches against those findings. Do not assume NVIDIA,
CUDA, Vulkan, Rust, C++, or a game engine is mandatory. Consult current primary
documentation for the chosen libraries and build toolchain. Record the decision,
why it fits the GPU, the tradeoffs, and how to reproduce the build.

GPU graphics and GPU pose inference are separate work items. Keep the initial
CPU MediaPipe producer working if needed while implementing actual GPU graphics.
Profile inference separately; a faster renderer alone does not guarantee the
desired end-to-end tracking frame rate.

## Data and control contracts

- Preserve existing HTTP/WebSocket command behavior where practical; keep scene,
  effect, settings, per-person and cue names consistent with the source catalog.
- Define a versioned renderer protocol with command IDs/acknowledgements, state
  snapshots, desired versus actual projector state, errors, health, and restart
  behavior. Do not send arbitrary Python objects across the native boundary.
- Define frame width/height/stride/pixel format, color space, timestamp, sequence,
  ownership and producer/consumer synchronization explicitly. Current camera and
  CPU composition buffers are BGR; handle conversion intentionally.
- Use bounded shared buffers or an appropriate local transport for frame/mask
  data. Prefer the newest complete frame, drop stale work, and prevent torn reads.
  Do not carry full raw video frames in HTTP, WebSocket JSON, or an unbounded queue.
- Preserve normalized pose/mask coordinates and mirroring, stable IDs, track
  expiry, per-person defaults/overrides, and gesture cooldown semantics.
- Keep camera, tracking, output, and browser preview resolutions/rates independent.
  Preserve letterboxing and overlay alignment at different aspect ratios.
- Keep most composition and history on the GPU: sprite transforms/alpha blending,
  particle drawing, glow/lightning, ghost accumulation, masks, and final output.
  Upload camera/mask input as needed; minimize full-frame GPU-to-CPU round trips.
- Preview generation must be throttled and decoupled. A slow browser, JPEG encode,
  screenshot request, or disconnected controller must not block presentation.
- Handle renderer loss/restart, GPU/device loss, camera disconnect, model failure,
  monitor changes, fullscreen, output close, and orderly shutdown with clear state.

## Implementation sequence

1. **Baseline:** install and validate the existing app; record hardware and real
   timings. Preserve the original ZIP or a local baseline commit.
2. **Native skeleton:** create a renderer with its own window, monitor/fullscreen
   control, a camera texture/standby image, letterboxing, and health reporting.
   Validate the GPU is hardware-backed. Exercise browser disconnect/reconnect.
3. **Boundary:** bridge the current camera/pose/state producer to the renderer;
   document the protocol and backpressure. Keep a selectable CPU fallback while
   porting and make the active renderer visible in status.
4. **Effects:** port sprite/head effects and cues first, then skeletons, particles,
   ghost histories/segmentation, lightning and debug overlays. Reuse bundled
   artwork. Compare against reference renders and existing behavioral tests.
5. **Control plane:** retain the website's operator functions; expose actual
   renderer state, frame timing and errors, plus a small independent preview.
6. **Delivery:** provide reproducible build/setup/start/stop commands and an
   optional user-session service; validate physical projector operation and record
   limitations. Make GPU rendering the primary mode only when acceptance passes.

## Completion checks

- Report detected GPU/device/driver and backend. Demonstrate actual GPU composition
  with suitable timings/profiling; do not count software rendering as GPU success.
- Start with the existing 1920×1080 / 30 FPS target and measure steady-state CPU
  use, GPU use, render frame time (median/p95), camera-to-display latency, memory,
  and dropped/stale frames. Record what scenes/people/effects were active. Do not
  promise a rate before testing on the destination hardware.
- Separate capture, inference, composition, preview encode and presentation costs.
  Test representative four-person loads and the all-effects/all-cues stress case.
- Preserve all five scenes, ten effects, seven animated cues, manual triggers,
  person assignment behavior, gestures, standby, resets, controls and art.
- Check 4:3 video on 16:9 output, HD sizing, correct mirroring, head/body placement,
  transparency, segmentation edges, and stable motion. Compare CPU references.
- Verify closing/reopening the website leaves the projector running and controls
  reconnect to the existing show. Verify slow/disconnected previews stay harmless.
- Test renderer restart/failure, camera stop/unplug/reconnect, monitor selection,
  fullscreen, clean shutdown, and bounded memory/latency during a sustained show.
- Exercise the physical Linux desktop/projector path and real tracked people;
  dummy SDL and synthetic poses are insufficient for hardware acceptance.
- Run without network after setup. Provide dependency/toolchain versions, build
  steps, launch/service instructions, meaningful tests, measured results, and a
  fallback/rollback procedure. Avoid adding network exposure to the local API.
