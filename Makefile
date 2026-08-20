# PolyMarket-Extractor convenience commands
.PHONY: demo api db-up db-down requirements venv

venv:
	python -m venv .venv
	.\\venv\\Scripts\\activate || . .venv/bin/activate

requirements:
	pip install -r backend/requirements.txt

demo:
	python -m backend.scripts.demo

api:
	cd backend && uvicorn app.main:app --reload --port 8000

db-up:
	docker compose -f infra/docker-compose.yml up -d db

db-down:
	docker compose -f infra/docker-compose.yml down
