"""Gamma API ingestor (LIVE data) — stdlib-only.

Source: https://gamma-api.polymarket.com (public, read-only).
Async pull of active markets -> normalizes -> upserts into live schema.
Uses stdlib urllib so the demo runs with no third-party dependencies.
"""
from __future__ import annotations

import asyncio
import json
import time as _t
import urllib.request

from ..config import settings
from ..db.database import Database

CATEGORY_KEYWORDS = {
    "politics": ["president", "election", "senate", "congress", "trump", "biden",
                 "governor", "mayor", "vote", "candidate", "democrat", "republican",
                 "party", "administration", "policy", "supreme court", "ukraine",
                 "israel", "gaza", "china", "russia", "wars"],
    "sports": ["nfl", "nba", "nhl", "mlb", "super bowl", "champions", "player",
               "team", "game", "match", "tournament", "goal", "points", "world cup",
               "olympics"],
    "crypto": ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp", "crypto",
               "dogecoin", "doge", "coin", "token", "etf", "halving"],
    "culture": ["oscar", "grammy", "movie", "film", "tv show", "celebrity", "music",
                "award", "haircut", "song", "album", "broadway", "netflix"],
    "economy": ["fed", "interest rate", "inflation", "gdp", "recession", "unemployment",
                "jobs report", "cpi", "economy"],
    "tech": ["ai", "openai", "apple", "google", "microsoft", "tesla", "spacex",
             "rocket", "launch", "iphone", "chip"],
}


def classify_category(question: str) -> str:
    q = (question or "").lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in q for k in kws):
            return cat
    return "other"


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _http_get_json(url: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers={"User-Agent": "PolyMarket-Extractor/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_market(raw: dict) -> dict:
    q = raw.get("question") or raw.get("title") or ""
    return {
        "id": str(raw.get("conditionId") or raw.get("id") or raw.get("marketId")),
        "slug": raw.get("slug"),
        "question": q,
        "category": classify_category(q),
        "source": "gamma",
        "status": raw.get("status", "active") or "active",
        "start_date": raw.get("startDate") or raw.get("createdAt"),
        "end_date": raw.get("endDate"),
    }


def normalize_price(raw: dict) -> dict:
    return {
        "time": int(_t.time()),
        "market_id": str(raw.get("conditionId") or raw.get("marketId") or raw.get("id")),
        "token_id": raw.get("tokenID") or raw.get("tokenId"),
        "outcome": raw.get("outcome") or "YES",
        "price": _f(raw.get("price")),
        "volume_24h": _f(raw.get("volume24hr") or raw.get("volume24h")),
        "liquidity": _f(raw.get("liquidity")),
        "spread": None,
    }


class GammaIngestor:
    def __init__(self, db: Database):
        self.db = db

    async def run_once(self, limit: int | None = None) -> dict:
        limit = limit or settings.live_limit
        url = f"{settings.gamma_base}/markets?active=true&limit={limit}"

        try:
            raw = await asyncio.to_thread(_http_get_json, url)
        except Exception as e:  # noqa: BLE001
            return {"source": "gamma", "offline": True, "error": str(e)}

        markets = [normalize_market(m) for m in raw]
        inserted_markets = 0
        inserted_prices = 0

        for m in markets:
            try:
                await self.db.upsert(
                    "live.markets",
                    conflict_cols=["id"],
                    data=m,
                    update_cols=["question", "category", "status", "updated_at"],
                )
                inserted_markets += 1
            except Exception as e:  # noqa: BLE001
                print(f"[gamma] market upsert failed ({m['id']}): {e}")

        for m in raw[:limit or 50]:
            pm = normalize_price(m)
            try:
                await self.db.upsert(
                    "live.prices",
                    conflict_cols=["time", "market_id", "outcome"],
                    data=pm,
                    update_cols=["price", "volume_24h", "liquidity", "spread"],
                )
                inserted_prices += 1
            except Exception:  # noqa: BLE001
                pass

        return {
            "source": "gamma",
            "markets_fetched": len(raw),
            "markets_upserted": inserted_markets,
            "prices_upserted": inserted_prices,
        }
