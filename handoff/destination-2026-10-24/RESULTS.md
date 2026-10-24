# Destination verification — 2026-10-24

All 144 transfer files verified before edits. Baseline: 55 unit tests and 16 smoke
checks passed. Current: 62 unit tests and 17 smoke checks passed. One pre-existing
Starlette/AnyIO deprecation warning remains. Native imports, pinned package checks,
pip check, bundled model digest, and reference-image inference passed.

GPU shader tests and a composition image passed on Mesa llvmpipe software EGL,
not on NVIDIA. Native window startup failed with GLX BadValue. No physical camera
or projector was validated. No drivers or services were changed.

## Synthetic CPU benchmark

640x480 synthetic input, 1920x1080 output, four synthetic pose/mask observations
over two painted demo figures, 30 FPS target, SDL dummy presentation. Normal case
uses pumpkin heads; stress enables every effect for every pose and retriggers
all cues/particles/lightning each second. Each recorded sample window is 7 seconds
after 2 seconds warm-up. Reference inference and other tests were stopped during
the final run. These are short diagnostics, not sustained physical acceptance.

| Case | Processing FPS | Composition median / p95 ms | JPEG median / p95 ms |
| --- | ---: | ---: | ---: |
| normal | 18.3 | 16.68 / 17.17 | 2.10 / 2.64 |
| all_effects_all_cues | 4.9 | 172.20 / 190.16 | 2.23 / 3.63 |

JSON records capture generation/poll, software input age, copy, inference selection,
composition/control, publication, preview encoding, and dummy SDL presentation
separately. Synthetic image generation is substantial CPU work. Demo `inference`
means selecting already-synthetic poses, not MediaPipe inference. Dummy SDL timing
is not physical presentation or camera-to-photon latency. Preview replacements
are expected with a latest-only encoder. GPU use, GPU elapsed time, physical frame
drops, steady-state GPU memory, and real camera/display latency remain unmeasured.

## CPU inference probe

The bundled reference image produced one person / one mask; two side-by-side
copies produced two people / two masks. A separate 20-sample warm benchmark
reported 89.53 ms median / 108.76 ms p95 for the single reference. A tiled four-copy
image produced zero detections; its shorter 49.34 ms median is not a four-person
inference performance result. That probe ran alongside an earlier synthetic load;
its timings are indicative, not isolated performance measurements. Real people
and sustained camera tracking still need testing. GPU pose inference is unchanged.

## Interpretation and next action

The CPU stress composition is expensive enough to justify shader migration; no
measured GPU speedup is claimed. Native GPU/device/display access is the next
acceptance gate. Read `../DESTINATION_SETUP.md` for exact local commands, current
feature boundaries, environment limits, optional user-service instructions, and
rollback. The full CPU show remains primary until the remaining GPU effects,
controller integration, preview pipeline and physical acceptance are complete.
