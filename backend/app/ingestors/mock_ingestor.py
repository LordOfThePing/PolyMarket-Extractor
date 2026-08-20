"""Mock data ingestor (for backtesting / simulation).

Instead of pulling from the network, this generates deterministic synthetic
markets + simulated trades and writes them into the mock schema.
This makes backtesting reproducible and decoupled from live network state.
"""
from __future__ import annotations

import random
import time as _t
import uuid

from ..db.database import Database

MOCK_QUESTIONS = [
    ("Will Bitcoin exceed $100k by March 2025?", "crypto"),
    ("Will the Lakers win the NBA championship?", "sports"),
    ("Will the Democratic nominee win the 2024 election?", "politics"),
    ("Will Oppenheimer win Best Picture?", "culture"),
    ("Will the Fed cut rates in Q1?", "economy"),
    ("Will OpenAI release GPT-5 this year?", "tech"),
    ("Will Ethereum hit $5k in 2025?", "crypto"),
    ("Will the Cowboys make the Super Bowl?", "sports"),
]

STRATEGIES = ["confidence_threshold", "momentum_breakout", "mean_reversion"]


class MockIngestor:
    def __init__(self, db: Database, seed: int = 42):
        self.db = db
        self.seed = seed

    async def run_once(self, n_trades: int = 60, strategy: str = "confidence_threshold") -> dict:
        rng = random.Random(self.seed)
        run_id = f"run-{strategy}-{int(_t.time())}"
        started = int(_t.time())

        # 1. simulated markets
        inserted_markets = 0
        for q, cat in MOCK_QUESTIONS:
            mid = f"mock-{cat}-{abs(hash(q)) % 100000}"
            try:
                await self.db.upsert(
                    "mock.markets",
                    conflict_cols=["id"],
                    data={"id": mid, "slug": None, "question": q, "category": cat},
                    update_cols=["question"],
                )
                inserted_markets += 1
            except Exception as e:  # noqa: BLE001
                print(f"[mock] market upsert failed: {e}")

        # 2. simulate trades
        trades = 0
        wins = 0
        pnl = 0.0
        for _ in range(n_trades):
            q, cat = rng.choice(MOCK_QUESTIONS)
            mid = f"mock-{cat}-{abs(hash(q)) % 100000}"
            entry = round(rng.uniform(0.3, 0.9), 3)
            p = rng.random()
            if p < 0.55:
                exit_price, result = round(entry + rng.uniform(0.05, 0.6), 3), "win"
                wins += 1
            elif p < 0.85:
                exit_price, result = round(entry - rng.uniform(0.05, 0.4), 3), "loss"
            else:
                exit_price, result = entry, "push"
            size = round(rng.uniform(50, 500), 2)
            pnl_usd = round((exit_price - entry) * 100 * size, 2)
            pnl += pnl_usd
            try:
                await self.db.execute(
                    """INSERT INTO mock_trades
                       (run_id, strategy, market_id, outcome, entry_price, exit_price,
                        size, pnl_usd, pnl_pct, result, entered_at, exited_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, strategy, mid, "YES", entry, exit_price, size,
                     pnl_usd, round((exit_price - entry) / entry * 100, 2),
                     result, started - rng.randint(1, 600), started),
                )
                trades += 1
            except Exception as e:  # noqa: BLE001
                print(f"[mock] trade insert failed: {e}")

        win_rate = round(wins / trades * 100, 2) if trades else 0
        roi = round(pnl / max(1, trades * 100), 2)

        # 3. record the run summary
        try:
            await self.db.upsert(
                "mock.runs",
                conflict_cols=["run_id"],
                data={"run_id": run_id, "strategy": strategy,
                      "params": f'{{"n_trades":{n_trades}}}',
                      "started_at": started, "finished_at": started,
                      "status": "completed", "total_trades": trades,
                      "win_rate": win_rate, "roi_pct": roi, "realized_pnl": pnl},
                update_cols=["status", "total_trades", "win_rate", "roi_pct", "realized_pnl"],
            )
        except Exception as e:  # noqa: BLE001
            print(f"[mock] run upsert failed: {e}")

        return {
            "source": "mock",
            "run_id": run_id,
            "strategy": strategy,
            "trades": trades,
            "win_rate_pct": win_rate,
            "roi_pct": roi,
            "realized_pnl_usd": pnl,
            "markets_upserted": inserted_markets,
        }
