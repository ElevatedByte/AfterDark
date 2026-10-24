#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
if [[ ! -x .venv/bin/python ]]; then
  echo 'Missing local .venv. Follow handoff/DESTINATION_SETUP.md.' >&2
  exit 1
fi
export HOST=127.0.0.1
export PYGAME_HIDE_SUPPORT_PROMPT=1
export PROJECTOR_MONITOR="${PROJECTOR_MONITOR:-0}"
export FULLSCREEN="${FULLSCREEN:-false}"
export MPLCONFIGDIR="$PWD/work/matplotlib"
mkdir -p "$MPLCONFIGDIR"
exec .venv/bin/python -m app.main "$@"
