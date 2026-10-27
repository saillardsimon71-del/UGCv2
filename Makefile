.PHONY: install dev run test demo seed build
install:
	python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install --no-audit --no-fund
build:
	cd frontend && npm run build
dev:  ## API :8000 + UI :5173 (proxy /api)
	.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 & \
	cd frontend && npm run dev; kill %1
run: build  ## un seul process : UI + API sur :8000
	.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
test:
	.venv/bin/python -m pytest tests/ -q
demo:
	.venv/bin/python scripts/demo_offline.py
seed:
	.venv/bin/python scripts/seed_demo.py
