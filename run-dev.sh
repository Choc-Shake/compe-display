#!/usr/bin/env bash
# Run the display on this computer for testing: http://localhost:8787
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8787 --reload
