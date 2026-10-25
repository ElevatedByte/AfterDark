# Afterdark — transfer to your new Linux computer

Packaged October 24, 2026. This is the existing Halloween Projector application,
with setup tools and a self-contained Codex handoff. The GPU engine is the next
development task; it has not been implemented in this snapshot.

## Transfer and open

1. Copy `Afterdark-Halloween-Transfer-2026-10-24.zip` to the new computer using a
   USB drive, shared folder, or your usual file transfer method.
2. Extract it into a writable development folder. Open the inner
   `afterdark-halloween` folder, which contains this file and `app/`.
3. In Codex, attach/open that extracted folder as the local project and make it
   the primary folder. Start a chat with local file and terminal access.
4. Paste the contents of `HANDOFF_PROMPT.txt` into that chat. The same prompt is
   supplied beside the ZIP for convenience. It asks Codex to install and verify
   the baseline, then implement the GPU renderer and browser control plane.

Local project folders provide file access; copying or syncing a conversation does
not transfer the source folder. With Codex CLI already installed, you can instead
run `codex` from the extracted project directory. See the official
[local project instructions](https://learn.chatgpt.com/docs/projects).

The projector app runs on the Linux computer itself. Its camera and display need
that computer's desktop session. Uploading the ZIP to a chat for analysis does
not by itself install dependencies or connect the chat to your physical devices.

## Install and run the baseline

Run commands from the extracted `afterdark-halloween` directory. Start with
**Python 3.11**, which is the tested interpreter. Internet is needed to install
Python packages; the model and artwork are already bundled. See
`handoff/PORTABILITY.md` for native packages and troubleshooting.

```bash
python3 scripts/verify_transfer.py
python3.11 setup_project.py --dev
python3.11 setup_project.py --check --dev
.venv/bin/python -m pytest
.venv/bin/python scripts/smoke_test.py
```

The setup helper creates `.venv`, installs pinned requirements, checks package
consistency, and verifies the bundled model's SHA-256. It does not start the
camera, projector, server, or a system service. `--dev` includes pytest and Ruff.
It requires an installed Python interpreter and working native system libraries.

Start with a synthetic rehearsal using monitor 0 and a window:

```bash
PROJECTOR_MONITOR=0 FULLSCREEN=false .venv/bin/python -m app.main --demo
```

Open [the controller](http://localhost:8000), then click **Start projector**.
Ctrl+C in the terminal stops the app. The smoke test uses synthetic people and a
dummy display; it is not a physical GPU/camera/projector test.

For a real camera and a second extended display:

```bash
PROJECTOR_MONITOR=1 .venv/bin/python -m app.main
```

Use monitor `0` if only one display is attached. Camera capture starts by default;
projector output starts separately from the controller. Use
`AUTO_START_CAMERA=false` if you want to start capture manually.

For persistent defaults, copy `.env.example` to `.env`, edit it, and use the
original Bash launcher:

```bash
cp .env.example .env
bash run.sh
```

`bash run.sh` loads `.env` as trusted shell configuration. Direct
`.venv/bin/python -m app.main` commands only read exported environment variables
and do **not** load `.env`. Defaults are localhost port 8000, camera 1280×720,
output 1920×1080, target 30 FPS, max eight people, fullscreen, monitor 1.

## What is included

| Location | Purpose |
| --- | --- |
| `app/` | Complete Python runtime, controller HTML/CSS/JS, effects and cues |
| `app/assets/` | Original artwork, sprite packs, prompts, and pose model |
| `requirements*.txt` | Original pinned direct runtime and development dependencies |
| `tests/`, `scripts/`, `run.sh` | Existing tests, diagnostics, previews, and Linux launcher |
| `setup_project.py` | Added portable environment installer/checker |
| `HANDOFF_PROMPT.txt`, `AGENTS.md` | Instructions for the receiving Codex |
| `handoff/` | Architecture, migration requirements, portability and verification |
| `README.md`, `VERIFICATION.md`, `artifacts/` | Original documentation and historical reference results/media |

The original application files are unchanged. The package omits virtual
environments, caches, logs, local secrets/configuration, and machine-specific
service state. There was no Git history in the source folder to preserve.
Optional sound recordings are absent in the original project. Historical images
and JSON reports under `artifacts/` are reference material, not current state.

This is a source package, not a fully offline installer: Python, system libraries,
GPU drivers, compilers, and Python wheel files must be available on the destination.
After successful dependency installation, the existing app runs locally/offline.

## Read next

- `handoff/PROJECT_CONTEXT.md`: what the app does and where the code lives.
- `handoff/PORTABILITY.md`: Linux setup, caveats, and package compatibility.
- `handoff/GPU_MIGRATION.md`: your requested next architecture and completion checks.
- `handoff/PACKAGE_VERIFICATION.md`: checks performed when this transfer was created.
