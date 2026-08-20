PRAGMA foreign_keys = ON;

-- SQLite-compatible schema for the QUICK DEMO.
-- Mirrors the 3-schema split (live / mock / resolved) but runs on SQLite
-- so the ingestion demo works without Docker/Postgres.
-- Production schema: db/migrations/001_create_schemas.sql (TimescaleDB).

CREATE TABLE IF NOT EXISTS live_markets (
    id          TEXT PRIMARY KEY,
    slug        TEXT,
    question    TEXT,
    category    TEXT,
    source      TEXT,
    status      TEXT,
    start_date  TEXT,
    end_date    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS live_prices (
    time        TEXT NOT NULL,
    market_id   TEXT NOT NULL,
    token_id    TEXT,
    outcome     TEXT,
    price       REAL,
    volume_24h  REAL,
    liquidity   REAL,
    spread      REAL,
    PRIMARY KEY (time, market_id, outcome)
);

CREATE TABLE IF NOT EXISTS live_orderbook (
    time        TEXT NOT NULL,
    market_id   TEXT NOT NULL,
    side        TEXT NOT NULL,
    price_level REAL NOT NULL,
    size        REAL NOT NULL,
    PRIMARY KEY (time, market_id, side, price_level)
);

CREATE TABLE IF NOT EXISTS mock_simulated_markets (
    id          TEXT PRIMARY KEY,
    slug        TEXT,
    question    TEXT,
    category    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mock_trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT,
    strategy    TEXT NOT NULL,
    market_id   TEXT NOT NULL,
    outcome     TEXT,
    entry_price REAL,
    exit_price  REAL,
    size        REAL,
    pnl_usd     REAL,
    pnl_pct     REAL,
    result      TEXT,
    entered_at  TEXT NOT NULL,
    exited_at   TEXT
);

CREATE TABLE IF NOT EXISTS mock_runs (
    run_id        TEXT PRIMARY KEY,
    strategy      TEXT,
    params        TEXT,
    started_at    TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at   TEXT,
    status        TEXT,
    total_trades  INTEGER,
    win_rate      REAL,
    roi_pct       REAL,
    realized_pnl  REAL
);

CREATE TABLE IF NOT EXISTS resolved_markets (
    id          TEXT PRIMARY KEY,
    slug        TEXT,
    question    TEXT,
    category    TEXT,
    end_date    TEXT,
    resolved_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS resolved_outcomes (
    market_id   TEXT NOT NULL REFERENCES resolved_markets(id),
    token_id    TEXT,
    outcome     TEXT,
    winning     INTEGER,
    final_price REAL,
    PRIMARY KEY (market_id, outcome)
);

CREATE TABLE IF NOT EXISTS resolved_predictions (
    market_id       TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    predicted_prob  REAL,
    resolved_prob   REAL,
    is_correct      INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (market_id, outcome)
);

CREATE TABLE IF NOT EXISTS resolved_category_performance (
    category        TEXT PRIMARY KEY,
    total_markets   INTEGER,
    win_count       INTEGER,
    loss_count      INTEGER,
    win_rate        REAL,
    roi_pct         REAL,
    volume_usd      REAL,
    liquidity       REAL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
