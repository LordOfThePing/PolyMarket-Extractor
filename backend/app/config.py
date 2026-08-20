"""Application configuration (stdlib-only so the demo runs without deps).

Reads environment variables with sensible defaults. The full FastAPI server
uses the same values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Database: "postgres" (TimescaleDB) or "sqlite" (quick demo)
    db_dialect: str = field(
        default_factory=lambda: os.getenv("DB_DIALECT", "sqlite"))
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite:///./data/polymarket_demo.db"))

    # Polymarket endpoints
    gamma_base: str = field(
        default_factory=lambda: os.getenv("GAMMA_BASE", "https://gamma-api.polymarket.com"))
    clob_base: str = field(
        default_factory=lambda: os.getenv("CLOB_BASE", "https://clob.polymarket.com"))
    clob_ws: str = field(
        default_factory=lambda: os.getenv(
            "CLOB_WS", "wss://ws-subscriptions-clob.polymarket.com/ws/market"))

    # Ingestion control
    ingestor_mode: str = field(default_factory=lambda: os.getenv("INGESTOR_MODE", "live"))
    live_poll_interval_s: float = field(
        default_factory=lambda: float(os.getenv("LIVE_POLL_INTERVAL_S", "60")))
    live_limit: int = field(default_factory=lambda: int(os.getenv("LIVE_LIMIT", "50")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Metadata
    app_name: str = "PolyMarket-Extractor API"
    version: str = "0.1.0"


settings = Settings()
