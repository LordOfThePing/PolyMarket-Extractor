# DB Schema Draft — 3 Schemas (PostgreSQL + TimescaleDB)

## live  (real-time markets — Gamma API + CLOB)

| table | key columns |
|-------|-------------|
| market        | id (PK), slug, question, category, status, end_date |
| price         | time (PK, hypertable), market_id, outcome, price, volume_24h, liquidity |
| orderbook     | time (PK, hypertable), market_id, side, price_level, size |

## mock  (strategy backtesting / simulation)

| table | key columns |
|-------|-------------|
| simulated_market | id (PK), slug, question, category |
| trade           | id (PK), run_id, strategy, market_id, entry_price, exit_price, pnl, result |
| run             | run_id (PK), strategy, params, win_rate, roi_pct, realized_pnl, status |

## resolved  (settled historical results for accuracy analysis)

| table | key columns |
|-------|-------------|
| market         | id (PK), slug, question, category, end_date, resolved_at |
| outcome        | market_id (PK), outcome (PK), winning, final_price |
| prediction     | market_id (PK), outcome (PK), predicted_prob, resolved_prob, is_correct |
| category_performance | category (PK), win_count, win_rate, roi_pct, volume, liquidity |

> Rationale: three physical schemas (live/mock/resolved) make the Live vs Mock
> vs Resolved separation a hard constraint — data from the three sources can
> never be mixed. Production DDL with hypertables lives in
> db/migrations/001_create_schemas.sql; an identical-shape SQLite variant
> (db/demo_sqlite.sql) powers the no-Docker quick demo.