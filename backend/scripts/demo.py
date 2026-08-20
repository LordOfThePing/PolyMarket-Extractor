#!/usr/bin/env python3
"""Quick demo of the data ingestion pipeline.

Runs LIVE (Gamma API), MOCK (synthetic backtest), and RESOLVED ingests
into their separate schemas, then prints the "Most Profitable Predictions"
ranking by category.

Usage:
    python -m scripts.demo                    # sqlite demo (no Docker needed)
    DATABASE_URL=postgresql://... python -m scripts.demo   # TimescaleDB
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analytics.engine import AnalyticsEngine  # noqa: E402
from app.config import settings  # noqa: E402
from app.db.database import Database  # noqa: E402
from app.ingestors.gamma_ingestor import GammaIngestor  # noqa: E402
from app.ingestors.mock_ingestor import MockIngestor  # noqa: E402
from app.ingestors.resolved_ingestor import ResolvedIngestor  # noqa: E402


async def main():
    dialect = settings.db_dialect
    print("=" * 64)
    print("PolyMarket-Extractor - Data Ingestion Pipeline Demo")
    print("Database dialect :", dialect)
    print("DB URL          :", settings.database_url)
    print("=" * 64)

    db = Database()
    await db.connect()
    await db.initialize()

    results = {}

    # ---- LIVE (Gamma API) -------------------------------------------
    print()
    print("[1/3] Ingesting LIVE data from Gamma API ...")
    try:
        live = await GammaIngestor(db).run_once(limit=30)
        results["live"] = live
        print(json.dumps(live, indent=2, default=str))
    except Exception as e:
        print("  live ingest failed:", e)

    # ---- MOCK (backtest simulation) ---------------------------------
    print()
    print("[2/3] Ingesting MOCK data (simulated backtest) ...")
    try:
        mock = await MockIngestor(db).run_once(n_trades=80)
        results["mock"] = mock
        print(json.dumps(mock, indent=2, default=str))
    except Exception as e:
        print("  mock ingest failed:", e)

    # ---- RESOLVED (historical accuracy) ------------------------------
    print()
    print("[3/3] Ingesting RESOLVED historical results ...")
    try:
        resolved = await ResolvedIngestor(db).run_once(limit=100)
        results["resolved"] = resolved
        print(json.dumps(resolved, indent=2, default=str))
    except Exception as e:
        print("  resolved ingest failed:", e)

    # ---- ANALYTICS ---------------------------------------------------
    print()
    print("=" * 64)
    print("ANALYTICS: Most Profitable Predictions by Category")
    print("=" * 64)
    engine = AnalyticsEngine(db)

    try:
        cats = await engine.category_performance()
        if cats:
            print(f"{'Category':<12}{'Markets':>8}{'WinRate%':>9}{'ROI%':>8}")
            for c in cats:
                print(f"{c['category']:<12}{c['total_markets']:>8}{c['win_rate_pct']:>9.2f}{c['roi_pct']:>8.2f}")
        else:
            print("  No resolved data ranked yet (resolved feed offline?). Run mock backtest for demo numbers.")
    except Exception as e:
        print("  category perf failed:", e)

    print()
    print("=" * 64)
    print("Row counts per schema")
    print("=" * 64)
    for logical in ["live.markets", "live.prices", "mock.runs", "resolved.markets"]:
        try:
            n = await db.count(logical)
            print(" ", logical.ljust(22), "->", n, "rows")
        except Exception as e:
            print(" ", logical.ljust(22), "-> error:", e)

    await db.close()
    print()
    print("Demo complete. To run the API server:  uvicorn app.main:app --reload")
    return results


if __name__ == "__main__":
    asyncio.run(main())
