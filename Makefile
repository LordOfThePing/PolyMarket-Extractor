# =====================================================================
# PolyMarket-Extractor — Makefile
# Targets are grouped: setup, database, demo, api, tests, docker, utility
#
# Windows:  mingw32-make / GNU make
# macOS/Linux: make
# =====================================================================

PY     := python
VENV   := .venv
PIP    := $(VENV)/bin/pip
PIPWIN := $(VENV)\Scripts\pip
PYVER  := python -c "import sys; print('%d.%d' % sys.version_info[:2])"

.PHONY: help setup venv requirements demo api tests lint         db-up db-down db-reset db-logs         up down logs ps         clean compile

# ---------------------------------------------------------------------
# HELP — default target
# ---------------------------------------------------------------------
help:
	@echo "PolyMarket-Extractor targets:"
	@echo "  setup          create venv + install backend deps"
	@echo "  requirements   install backend requirements into active (or venv) Python"
	@echo "  demo           run the end-to-end ingestion pipeline demo (SQLite)"
	@echo "  api            start FastAPI dev server on :8000"
	@echo "  tests          run backend tests (pytest if available)"
	@echo "  compile        syntax-check all backend python files"
	@echo "  lint           run a basic import sanity check"
	@echo ""
	@echo "  db-up          start TimescaleDB + backend via docker compose"
	@echo "  db-down        stop docker compose stack"
	@echo "  db-reset       destroy db volume + recreate (fresh schemas)"
	@echo "  db-logs        tail database (and backend) logs"
	@echo ""
	@echo "  up             alias for db-up"
	@echo "  down           alias for db-down"
	@echo "  logs           tail all stack logs"
	@echo "  ps             show running services"
	@echo ""
	@echo "  clean          remove venv, caches, temp and local db files"

clean:
	cd backend && $(PY) scripts/clean.py

# ---------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------
venv:
	$(PY) -m venv $(VENV)
	@echo "venv created at ./$(VENV)"

requirements:
	$(PIP) install -r backend/requirements.txt || $(PIPWIN) install -r backend/requirements.txt

setup: venv requirements
	@echo ""
	@echo "Setup complete."
	@echo "  Next:  make demo        (run the pipeline demo)"
	@echo "         make api         (start the FastAPI server)"

# ---------------------------------------------------------------------
# PYTHON (backend)
# ---------------------------------------------------------------------
demo:
	@echo "== Running ingestion pipeline demo (live + mock + resolved) =="
	cd backend && python -m scripts.demo

api:
	@echo "== Starting FastAPI at http://127.0.0.1:8000 =="
	cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

compile:
	cd backend && python -m py_compile \
		app/config.py app/main.py app/db/database.py \
		app/ingestors/gamma_ingestor.py app/ingestors/clob_ingestor.py \
		app/ingestors/mock_ingestor.py app/ingestors/resolved_ingestor.py \
		app/analytics/engine.py app/models/schemas.py app/api/routes.py \
		scripts/demo.py

tests:
	cd backend && python -m pytest -q tests || echo "pytest not found — install with: pip install pytest"

lint:
	cd backend && python -c "import app.main; print('import OK')"

# ---------------------------------------------------------------------
# DATABASE (Docker + TimescaleDB)
# ---------------------------------------------------------------------
db-up:
	docker compose -f infra/docker-compose.yml up -d
	@echo "TimescaleDB + backend starting.  db: localhost:5432 (pm/pm/polymarket)"

db-down:
	docker compose -f infra/docker-compose.yml down

db-reset:
	docker compose -f infra/docker-compose.yml down -v
	docker compose -f infra/docker-compose.yml up -d
	@echo "db volume recreated"

db-logs:
	docker compose -f infra/docker-compose.yml logs -f db

# ---------------------------------------------------------------------
# DOCKER COMPOSE ALIASES
# ---------------------------------------------------------------------
up: db-up
down: db-down
logs: 
	docker compose -f infra/docker-compose.yml logs -f
ps:
	docker compose -f infra/docker-compose.yml ps