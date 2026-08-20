# Demo Walkthrough & Video Script

This file doubles as the written demo walkthrough you can screen-record for your
**video update** — each section is a bite-size scene with the on-screen framing
and the narration line.

---

## Scene 1 — Repo structure (the 3-way separation)

**On screen:** the repo tree (backend/ + db/ + infra/ + scripts/).

> "Today's deliverable is a production-shaped repository with one non-negotiable:
> a hard separation of Live, Mock and Resolved Polymarket data across three
> dedicated database schemas."
>
> - **Live** → Gamma API + CLOB (REST + WebSocket) → base: live schema
> - **Mock** → simulated strategy backtests → mock schema
> - **Resolved** → settled historical markets → resolved schema

---

## Scene 2 — Database schema (3 schemas on TimescaleDB)

**On screen:** db/migrations/001_create_schemas.sql

> "Three PostgreSQL/TimescaleDB schemas. Prices and orderbooks are hypertables for
> time-series performance. Each source writes only to its own schema, so Live is
> never contaminated by Mock, and accuracy analysis only reads settled Resolved data."

---

## Scene 3 — Run the pipeline demo

**On screen:** terminal running the demo.

> "One command spins up the whole ingestion demo — no Docker required because it
> falls back to SQLite with the identical 3-schema shape:"
>
>     python -m venv .venv
>     pip install -r backend/requirements.txt
>     cd backend && python -m scripts.demo
>
> "The script ingests LIVE markets from the Polymarket Gamma API, generates a MOCK
> simulated backtest, pulls RESOLVED history, then prints the headline deliverable:
> **Most Profitable Predictions ranked by category** (ROI + win rate)."

---

## Scene 4 — The analytics output

**On screen:** the ranked table of categories with wins / win-rate / ROI.

> "Here is the payoff: per-category ROI and win rate computed from real resolved
> predictions, exactly what we wanted to show as 'Most Profitable Predictions'."

---

## Scene 5 — API server

**On screen:** uvicorn serving GET /api/analytics/most-profitable

> "The full pipeline is also exposed as a FastAPI service — ingestion and analytics
> endpoints — ready to be driven by a Next.js or Streamlit dashboard with
> Live | Mock | Resolved tabs, category/date filters and CSV export."

---

## Next steps (clearly stubbed in the repo)

- **Live scheduled polling + CLOB WebSocket streaming** already scaffolded
- **Next.js/Streamlit dashboard** with tabs + CSV export
- **Docker deployment + monitoring** (logging, error alerts) via infra/
- **Backtesting module** running mock strategies against resolved history
