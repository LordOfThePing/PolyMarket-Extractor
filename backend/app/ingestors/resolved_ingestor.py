"""Resolved historical results ingestor (stdlib-only).

Pulls settled markets + their final outcomes from the Gamma API
(closed/resolved markets) and writes them into the resolved schema for
accuracy analysis and backtesting.
"""
from __future__ import annotations

import asyncio
import json
import time as _t
import urllib.request

from ..config import settings
from ..db.database import Database
from .gamma_ingestor import classify_category


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_json_list(s):
    """Parse a JSON-encoded string list like '["Yes","No"]' -> python list."""
    if not s:
        return []
    if isinstance(s, list):
        return s
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _http_get_json(url: str, timeout: float = 20.0):
    req = urllib.request.Request(url, headers={"User-Agent": "PolyMarket-Extractor/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class ResolvedIngestor:
    def __init__(self, db: Database):
        self.db = db

    async def run_once(self, limit: int = 100) -> dict:
        url = f"{settings.gamma_base}/markets?closed=true&limit={limit}"
        try:
            raw = await asyncio.to_thread(_http_get_json, url)
        except Exception as e:
            return {"source": "resolved", "offline": True, "error": str(e)}

        inserted_markets = 0
        inserted_outcomes = 0
        inserted_predictions = 0
        wins = 0

        for m in raw:
            mid = str(m.get("conditionId") or m.get("id") or m.get("marketId"))
            q = m.get("question") or ""
            outcomes = _parse_json_list(m.get("outcomes"))
            prices_raw = _parse_json_list(m.get("outcomePrices")) or _parse_json_list(m.get("outcome_prices"))
            prices = [_f(p) for p in prices_raw]

            # Determine winner(s): index whose settled price == 1.
            winner_idx = [i for i, p in enumerate(prices) if p is not None and p >= 0.99]

            try:
                await self.db.upsert(
                    "resolved.markets",
                    conflict_cols=["id"],
                    data={"id": mid, "slug": m.get("slug"), "question": q,
                          "category": classify_category(q), "end_date": m.get("endDate")},
                    update_cols=["question", "category"],
                )
                inserted_markets += 1
            except Exception as e:
                print(f"[resolved] market upsert failed: {e}")

            # One row per outcome.
            for i, outcome in enumerate(outcomes):
                price = prices[i] if i < len(prices) else None
                is_winner = i in winner_idx
                resolved_prob = 100.0 if is_winner else 0.0
                # predicted_prob before resolution: approximate from pre-settle price.
                pred = price if price is not None else 50.0
                try:
                    await self.db.upsert(
                        "resolved.outcomes",
                        conflict_cols=["market_id", "outcome"],
                        data={"market_id": mid, "token_id": None, "outcome": outcome,
                              "winning": 1 if is_winner else 0, "final_price": price},
                        update_cols=["winning", "final_price"],
                    )
                    inserted_outcomes += 1
                except Exception as e:
                    print(f"[resolved] outcome upsert failed: {e}")
                try:
                    await self.db.upsert(
                        "resolved.predictions",
                        conflict_cols=["market_id", "outcome"],
                        data={"market_id": mid, "outcome": outcome,
                              "predicted_prob": pred, "resolved_prob": resolved_prob,
                              "is_correct": 1 if is_winner else 0},
                        update_cols=["predicted_prob", "resolved_prob", "is_correct"],
                    )
                    inserted_predictions += 1
                    if is_winner:
                        wins += 1
                except Exception as e:
                    print(f"[resolved] prediction upsert failed: {e}")

        # Refresh aggregated category performance.
        import re
        await self._refresh_category_performance()

        return {"source": "resolved", "markets_fetched": len(raw),
                "markets_upserted": inserted_markets,
                "outcomes_upserted": inserted_outcomes,
                "predictions_upserted": inserted_predictions,
                "winning_outcomes": wins}

    async def _refresh_category_performance(self):
        """Recompute resolved.category_performance from prediction rows."""
        q = """
            SELECT
              rm.category,
              COUNT(*) AS n,
              SUM(CASE WHEN rp.is_correct=1 THEN 1 ELSE 0 END) AS wins,
              SUM(CASE WHEN rp.is_correct=0 THEN 1 ELSE 0 END) AS losses,
              AVG(rp.predicted_prob) AS avg_prob
            FROM resolved.predictions rp JOIN resolved.markets rm ON rm.id=rp.market_id
            GROUP BY rm.category
        """
        if self.db.dialect == "sqlite":
            q = (q.replace("resolved.predictions", "resolved_predictions")
                  .replace("resolved.markets", "resolved_markets")
                  .replace("rm.", "rm.").replace("rp.", "rp."))
        try:
            rows = await self.db.fetch(q)
        except Exception as e:
            print(f"[resolved] category perf refresh failed: {e}")
            return
        for r in rows:
            cat = r["category"]
            n = int(r.get("n") or 0)
            wins = int(r.get("wins") or 0)
            losses = int(r.get("losses") or 0)
            avg_prob = float(r.get("avg_prob") or 0)
            win_rate = round(wins / n * 100, 2) if n else 0.0
            notional = n * 100.0
            collected = 100.0 * wins
            roi = round((collected - notional) / max(notional, 1) * 100, 2)
            try:
                await self.db.upsert(
                    "resolved.categories",
                    conflict_cols=["category"],
                    data={"category": cat, "total_markets": n, "win_count": wins,
                          "loss_count": losses, "win_rate": win_rate, "roi_pct": roi,
                          "volume_usd": 0, "liquidity": 0},
                    update_cols=["total_markets", "win_count", "loss_count",
                                 "win_rate", "roi_pct", "updated_at"],
                )
            except Exception as e:
                print(f"[resolved] cat perf upsert failed: {e}")