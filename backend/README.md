# PolyMarket-Extractor — Backend

Python 3.10+ / **FastAPI** / **asyncio** data ingestion + analytics service that
feeds the Live / Mock / Resolved **TimescaleDB** schemas.

## Quick start (demo, SQLite — no Docker needed)

```bash
cd backend
pip install -r requirements.txt
python -m scripts.demo          # run the ingestion pipeline demo
```

## Run the FastAPI server

```bash
uvicorn app.main:app --reload --port 8000
# health:  GET /health
# ingest:  POST /api/ingest/live | /api/ingest/mock | /api/ingest/resolved
# analytics: GET /api/analytics/categories
#           GET /api/analytics/most-profitable?category=politics
#           GET /api/analytics/mock-runs
```

## Use TimescaleDB (production)

Copy .env.example → .env and set:

```
DB_DIALECT=postgres
DATABASE_URL=postgresql://pm:pm@localhost:5432/polymarket
```

Then start the stack:

```bash
docker compose -f ../infra/docker-compose.yml up -d
```

## Layout

```
app/
├─ ingestors/     gamma, clob (rest+ws), mock, resolved
├─ analytics/     ROI/winrate/volume engine
├─ db/            async dialect-agnostic wrapper (postgres | sqlite)
├─ api/           ingestion + analytics routes
├─ models/        pydantic schemas
└─ main.py        FastAPI entrypoint
scripts/demo.py   end-to-end pipeline demo
```
