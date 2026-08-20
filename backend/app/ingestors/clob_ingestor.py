"""CLOB API ingestor (LIVE data).

Polymarket CLOB is the orderbook / trading engine used by Polymarket.
We ingest two things:
  - CLOB REST: market books (bids/asks) -> live.orderbook
  - CLOB WebSocket: real-time market updates -> live.orderbook (streaming)

Public market/price feeds work without auth; private endpoints need an
L2 auth header. We implement the public feed patterns.
"""
from __future__ import annotations

import asyncio
import json
import time as _t

import httpx

from ..config import settings
from ..db.database import Database


class ClobRestIngestor:
    """Pull market books from CLOB REST (/book)."""

    def __init__(self, db: Database):
        self.db = db

    async def run_once(self, market_ids: list[str] | None = None) -> dict:
        market_ids = market_ids or []
        book_url = f"{settings.clob_base}/book"
        results = {"source": "clob_rest", "books_fetched": 0, "rows_inserted": 0}

        async with httpx.AsyncClient(timeout=15) as client:
            for mid in market_ids:
                try:
                    resp = await client.get(book_url, params={"token_id": mid})
                    if resp.status_code != 200:
                        continue
                    book = resp.json()
                    results["books_fetched"] += 1
                    inserted = await self._store_book(mid, book)
                    results["rows_inserted"] += inserted
                except Exception as e:  # noqa: BLE001
                    print(f"[clob_rest] book failed for {mid}: {e}")
                await asyncio.sleep(0.05)
        return results

    async def _store_book(self, token_id: str, book: dict) -> int:
        rows = 0
        now = int(_t.time())
        for side, items in (("buys", book.get("bids", [])),
                            ("sells", book.get("asks", []))):
            for level in items[:20]:  # top 20 levels
                price = float(level.get("price") or 0)
                size = float(level.get("size") or level.get("amount") or 0)
                try:
                    await self.db.execute(
                        self._insert_book_sql(),
                        (now, token_id, side, price, size),
                    )
                    rows += 1
                except Exception:
                    pass
        return rows

    def _insert_book_sql(self) -> str:
        if self.db.dialect == "postgres":
            return ("INSERT INTO live.orderbook (time, market_id, side, price_level, size) "
                    "VALUES (%s,%s,%s,%s,%s)")
        return ("INSERT INTO live_orderbook (time, market_id, side, price_level, size) "
                "VALUES (?,?,?,?,?)")


class ClobWsIngestor:
    """Subscribe to CLOB market WebSocket and stream price/orderbook updates.

    Public market updates are available on the CLOB websocket. This class
    demonstrates the connection + subscription pattern and is safe to run
    (reconnect + graceful shutdown + run_for() bounded helper).
    """

    def __init__(self, db: Database, market_ids: list[str] | None = None):
        self.db = db
        self.market_ids = market_ids or []
        self._running = False

    async def stream(self, on_message=None):
        import websockets
        self._running = True
        url = settings.clob_ws
        while self._running:
            try:
                async with websockets.connect(url) as ws:
                    await ws.send(json.dumps({"assets_ids": self.market_ids}))
                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw)
                            if on_message:
                                await on_message(msg)
                        except Exception:
                            continue
            except Exception as e:  # noqa: BLE001
                print(f"[clob_ws] connection lost: {e}; reconnecting in 3s")
                await asyncio.sleep(3)

    def stop(self):
        self._running = False

    async def run_for(self, seconds: int, on_message=None) -> int:
        counter = {"n": 0}

        async def _count(msg):
            counter["n"] += 1
            if on_message:
                await on_message(msg)

        task = asyncio.create_task(self.stream(on_message=_count))
        await asyncio.sleep(seconds)
        self.stop()
        task.cancel()
        return counter["n"]
