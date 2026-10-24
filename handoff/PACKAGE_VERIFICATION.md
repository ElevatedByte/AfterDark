# Transfer verification — October 24, 2026

Verified on the source Linux x86_64 computer, using Python 3.11.15 and a newly
created virtual environment in a temporary copy. These are transfer/baseline
checks, not validation of the future GPU renderer or destination hardware.

## Passed

- Copied **130 original project files**, including the model, artwork, tests,
  documentation and historical reference media. All copied originals were checked
  byte-for-byte against the source. Only new handoff/setup/integrity files were added.
- Created a fresh virtual environment and ran `setup_project.py --dev` with package
  downloads. All original runtime/dev pins installed successfully. `pip check`,
  exact runtime version check, and bundled pose-model digest check passed.
- Ran `setup_project.py --check --dev` successfully without installation.
- **55 tests passed** in 2.99 seconds in the fresh environment. One existing
  Starlette/AnyIO deprecation warning remains.
- Ruff checks passed for `app`, `scripts`, `tests`, and `setup_project.py`.
  Formatting checks passed for the added Python helpers; Bash syntax check passed
  for the original `run.sh`.
- **All 16 end-to-end smoke checks passed** with a localhost test server, synthetic
  people, and SDL dummy display. They cover scenes/effects/cues, per-person defaults,
  previews/native output dimensions, HTTP/WebSocket controls, projector/fullscreen
  lifecycle, restarts, and shutdown with a connected preview.
- Real MediaPipe CPU model initialization and reference-image inference passed:
  one person/one mask from the single reference, and two people/two masks from two
  copies. This did not use the webcam and does not measure sustained show speed.
- Final ZIP CRC check, safe relative paths, extraction round trip, manifest hashes,
  source-file equality, and standalone-prompt equality were checked. The integrity
  verifier was also checked against an intentionally altered test copy.

Fresh result JSON is in `transfer-smoke-test.json` and
`transfer-tracking-probe.json`. The smoke sample was 15.9 synthetic processing FPS
and 0.17-second shutdown; it is not a real-camera, GPU, or future-machine benchmark.
Original `artifacts/` reports have been retained unchanged as historical evidence.

`verified-environment-linux-py311.txt` records the fresh resolved dependencies.
`source-environment.txt` records the pre-existing environment. The original
requirements pin direct dependencies, so some freshly resolved transitive versions
differ. Tests passed against the freshly installed set.

## Execution environment notes

The initial sandboxed unit-test attempt stalled after 12 tests because the API
test client's loopback/event-loop access was restricted; it was interrupted.
The complete suite and smoke test then passed with host loopback access, using only
the isolated temporary copy. The model probe also used the host native-library
environment. No live service, webcam, or physical projector was started or changed.
An offline-cache install attempt found missing cached packages, so the actual
fresh install used downloads. Package wheels are not bundled in the ZIP.

## Still required on the new computer

Install/validate its native libraries and Python packages, detect its GPU and
driver, test camera capture and actual people, verify physical projector routing
and any audio, and implement/measure the GPU migration. There is no compiled GPU
service in this package yet. The original app continues to use CPU graphics and
CPU MediaPipe inference.

The ZIP excludes virtual environments, caches, logs, machine-specific secrets and
service configuration. All setup and verification additions are visible source.
`SHA256SUMS.json` hashes each packaged file except itself; the adjacent ZIP SHA-256
file covers the archive. These are integrity checks, not signed provenance.
