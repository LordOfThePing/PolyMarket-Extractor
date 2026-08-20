# PolyMarket-Extractor — Architecture Sketch & Data Flow

## The 3-way data separation (core requirement)

```
        INGESTION  (FastAPI + asyncio, concurrent producers)
   ┌─────────────────────┬───────────────────┬─────────────────────┐
   ▼                     ▼                   ▼
 LIVE                 MOCK                 RESOLVED
 Gamma API            Strategy backtests   Settled historical
 CLOB REST            simulation           results
 CLOB WebSocket          │                    │
   │                    │                    │
   ▼                    ▼                    ▼
 live schema          mock schema          resolved schema
 (hypertables)        (hypertables)        (hypertables)
   └──────────────┬────┴────────────────────┘
                  ▼
        ANALYTICS ENGINE
   ROI, winrate, volume, liquidity per category
   -> "Most Profitable Predictions" (ranked)
                  ▼
        DASHBOARD  (Next.js / Streamlit)
   Tabs: Live | Mock | Resolved
   Filters: category / date.  Charts + CSV export
```

## How data flows

1. **Live** — Async workers poll the **Gamma API** (markets/prices) and
   **CLOB REST** (orderbook); a **WebSocket** subscriber streams real-time
   updates. All rows go only into the `live` schema (hypertables: markets,
   prices, orderbook).
2. **Mock** — A synthetic generator produces simulated markets + trades for
   deterministic backtesting. Writes to the `mock` schema + a `run` summary
   so every backtest is reproducible and clearly labeled as simulated (never
   mixed into live/resolved).
3. **Resolved** — A worker pulls **closed / settled markets** and their final
   winning outcomes. Writes to the `resolved` schema so accuracy analysis and
   backtests only ever touch real, settled history.

## Repo structure

```
PolyMarket-Extractor/
├─ backend/                  # Python 3.10+ / FastAPI / asyncio
│  ├─ app/
│  │  ├─ ingestors/          # gamma, clob (rest+ws), mock, resolved
│  │  ├─ analytics/          # ROI/winrate/volume engine
│  │  ├─ db/                 # async dialect-agnostic DB wrapper
│  │  ├─ api/                # ingestion + analytics routes
│  │  └─ main.py             # FastAPI entrypoint
│  └─ scripts/demo.py        # end-to-end pipeline demo
├─ db/
│  ├─ migrations/            # TimescaleDB DDL (3 schemas)
│  └─ demo_sqlite.sql        # identical shape, sqlite for quick demo
├─ infra/
│  └─ docker-compose.yml     # TimescaleDB + backend (monitoring-ready)
├─ Makefile                  # demo / api / db-up / db-down
└─ docs/                     # architecture + schema drafts
```

## Key engineering choices

- **Dialect-agnostic DB layer** — ingestors write once and run against both
  TimescaleDB (prod) and SQLite (demo) for a fast local loop.
- **Separate schemas = hard guarantee** — data cannot cross Live/Mock/Resolved
  boundaries at write time.
- **Hypertables** — prices/orderbook use TimescaleDB hypertables for
  time-series performance + downsampling.
- **Async everywhere** — httpx + websockets under asyncio for concurrent
  ingestion.
- **Composable ingestors** — each source is an independent class you can run,
  poll, or wire into the scheduler and monitoring later.
