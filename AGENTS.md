# Afterdark project handoff

Read `START_HERE.md`, `handoff/PROJECT_CONTEXT.md`, and
`handoff/GPU_MIGRATION.md` before working. `HANDOFF_PROMPT.txt` records the user's
intended next task. The original `README.md` and `VERIFICATION.md` contain useful
details plus historical paths, service state, and verification results.

This is a portable source snapshot, not an already implemented GPU renderer.
The user wants the primary rendering engine on the GPU, potentially as a compiled
native service/process, and the website to be a control plane. First establish a
working baseline on this computer; then migrate incrementally when requested.

Keep the local/offline show, independent projector window, all effects, scenes,
cues, gestures, per-person assignments, and original artwork working. Preserve
normalized camera coordinates, output aspect ratio, and bounded frame queues.
Keep hardware-dependent results distinct from synthetic/headless tests.

Use a new local `.venv`; do not copy an old virtual environment. Requirements are
in `requirements.txt` and `requirements-dev.txt`. Start with Python 3.11. Camera
capture currently forces Linux V4L2; Windows/macOS need a platform adapter.
There is no Node/frontend build step and no OpenAI API dependency in this app.

Typical checks after setup (Windows uses `.venv\\Scripts\\python.exe`):

```sh
.venv/bin/python -m pytest
.venv/bin/python -m ruff check app scripts tests setup_project.py
.venv/bin/python scripts/smoke_test.py
```

Run a single server worker. Use demo mode and SDL dummy for unattended checks;
use the logged-in graphical session for camera/projector acceptance. Do not
publish the control plane: it defaults to loopback and has no authentication.
The destination is Linux; its distribution and GPU are not yet known. Inspect
the actual machine before choosing a GPU stack. Record new decisions and verification in
the project so later chats do not depend on conversation history.
