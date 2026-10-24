#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
export PYGAME_HIDE_SUPPORT_PROMPT=1
setup_only=false
if [[ "${1:-}" == '--setup' ]]; then setup_only=true; shift; fi
if [[ ! -x .venv/bin/python ]]; then
  python_bin="${PYTHON_BIN:-}"
  if [[ -z "$python_bin" ]]; then
    for candidate in python3.11 python3.12 python3.13 python3; do
      if command -v "$candidate" >/dev/null 2>&1; then python_bin="$candidate"; break; fi
    done
  fi
  if [[ -z "$python_bin" ]]; then echo 'Install Python 3.11+ and python3-venv first.' >&2; exit 1; fi
  "$python_bin" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
  if command -v uv >/dev/null 2>&1; then uv venv --python "$python_bin" .venv
  else "$python_bin" -m venv .venv; fi
fi
if ! .venv/bin/python scripts/check_dependencies.py; then
  if command -v uv >/dev/null 2>&1; then uv pip install --python .venv/bin/python -r requirements.txt
  else .venv/bin/python -m pip install -r requirements.txt; fi
fi
model_path="${MODEL_PATH:-app/assets/models/pose_landmarker_lite.task}"
demo=false
for arg in "$@"; do [[ "$arg" == '--demo' ]] && demo=true; done
if [[ ! -f "$model_path" && "$demo" == false && "${DEMO_MODE:-false}" != true ]]; then
  .venv/bin/python scripts/download_model.py --output "$model_path"
fi
if [[ "$setup_only" == true ]]; then echo 'Setup complete. Runtime works offline. Run ./run.sh'; exit 0; fi
exec .venv/bin/python -m app.main "$@"
