#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || make install
[ -d frontend/dist ] || (cd frontend && npm run build)
.venv/bin/python scripts/seed_demo.py || true
exec .venv/bin/python -m uvicorn backend.app.main:app --host "${STUDIO_HOST:-0.0.0.0}" --port "${STUDIO_PORT:-8000}"
