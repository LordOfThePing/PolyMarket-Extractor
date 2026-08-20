-- =====================================================================
-- PolyMarket-Extractor
-- Database schema setup (PostgreSQL + TimescaleDB)
--
-- 3 SEPARATE SCHEMAS = one of the core requirements:
--   live     -> real-time markets from Gamma API + CLOB (WebSocket)
--   mock     -> simulated data for strategy backtesting / simulation
--   resolved -> settled historical markets for accuracy analysis
--
-- Each schema writes to its own hypertables so data can never be
-- accidentally mixed between Live / Mock / Resolved.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------
-- SCHEMA: live
-- ---------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS live;

CREATE TABLE IF NOT EXISTS live.markets (
    id              TEXT PRIMARY KEY,
    slug            TEXT,
    question        TEXT,
    category        TEXT,
    source          TEXT NOT NULL DEFAULT 'gamma',
    status          TEXT,
    start_date      TIMESTAMPTZ,
    end_date        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS live.prices (
    time            TIMESTAMPTZ NOT NULL,
    market_id       TEXT NOT NULL,
    token_id        TEXT,
    outcome         TEXT,
    price           NUMERIC,
    volume_24h      NUMERIC,
    liquidity       NUMERIC,
    spread          NUMERIC,
    PRIMARY KEY (time, market_id, outcome)
);

SELECT create_hypertable('live.prices', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS live.orderbook_snapshot (
    time            TIMESTAMPTZ NOT NULL,
    market_id       TEXT NOT NULL,
    side            TEXT NOT NULL,
    price_level     NUMERIC NOT NULL,
    size            NUMERIC NOT NULL,
    PRIMARY KEY (time, market_id, side, price_level)
);

SELECT create_hypertable('live.orderbook_snapshot', 'time', if_not_exists => TRUE);

-- ---------------------------------------------------------------------
-- SCHEMA: mock
-- ---------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS mock;

CREATE TABLE IF NOT EXISTS mock.simulated_markets (
    id              TEXT PRIMARY KEY,
    slug            TEXT,
    question        TEXT,
    category        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mock.trades (
    id              BIGSERIAL PRIMARY KEY,
    run_id          TEXT,
    strategy        TEXT NOT NULL,
    market_id       TEXT NOT NULL,
    outcome         TEXT,
    entry_price     NUMERIC,
    exit_price      NUMERIC,
    size            NUMERIC,
    pnl_usd         NUMERIC,
    pnl_pct         NUMERIC,
    result          TEXT,
    entered_at      TIMESTAMPTZ NOT NULL,
    exited_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS mock.runs (
    run_id          TEXT PRIMARY KEY,
    strategy        TEXT,
    params          JSONB,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT,
    total_trades    INT,
    win_rate        NUMERIC,
    roi_pct         NUMERIC,
    realized_pnl    NUMERIC
);

-- ---------------------------------------------------------------------
-- SCHEMA: resolved
-- ---------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS resolved;

CREATE TABLE IF NOT EXISTS resolved.markets (
    id              TEXT PRIMARY KEY,
    slug            TEXT,
    question        TEXT,
    category        TEXT,
    end_date        TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS resolved.outcomes (
    market_id       TEXT NOT NULL REFERENCES resolved.markets(id),
    token_id        TEXT,
    outcome         TEXT,
    winning         BOOLEAN,
    final_price     NUMERIC,
    PRIMARY KEY (market_id, outcome)
);

CREATE TABLE IF NOT EXISTS resolved.predictions (
    market_id       TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    predicted_prob  NUMERIC,
    resolved_prob   NUMERIC,
    is_correct      BOOLEAN,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market_id, outcome)
);

CREATE TABLE IF NOT EXISTS resolved.category_performance (
    category        TEXT PRIMARY KEY,
    total_markets   INT,
    win_count       INT,
    loss_count      INT,
    win_rate        NUMERIC,
    roi_pct         NUMERIC,
    volume_usd      NUMERIC,
    liquidity       NUMERIC,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_live_markets_category   ON live.markets(category);
CREATE INDEX IF NOT EXISTS idx_resolved_markets_cat    ON resolved.markets(category);
CREATE INDEX IF NOT EXISTS idx_mock_trades_run_id      ON mock.trades(run_id);
