"""Async DB wrapper.

Unified, dialect-agnostic API:
  - table(name)   maps logical table name -> physical (postgres uses schemas)
  - upsert(table, conflict_cols, data: dict)
  - insert(table, data: dict)
  - count(table)
  - fetch(query, params)   (query must be manually written dialect-aware)

Dialects:
  - "postgres" -> async psycopg against TimescaleDB (production)
  - "sqlite"   -> stdlib sqlite3 (quick demo, no Docker needed)
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Sequence

from ..config import settings

_DATA_DIR = Path("./data")
_DATA_DIR.mkdir(exist_ok=True)

# logical -> physical table names per dialect
_TABLES_SQLITE = {
    "live.markets": "live_markets",
    "live.prices": "live_prices",
    "live.orderbook": "live_orderbook",
    "mock.markets": "mock_simulated_markets",
    "mock.trades": "mock_trades",
    "mock.runs": "mock_runs",
    "resolved.markets": "resolved_markets",
    "resolved.outcomes": "resolved_outcomes",
    "resolved.predictions": "resolved_predictions",
    "resolved.categories": "resolved_category_performance",
}
_TABLES_POSTGRES = {k: k for k in _TABLES_SQLITE}  # already schema-qualified


def _col(prefix: str, c: str) -> str:
    """Postgres double-quotes column names to preserve camelCase/snake."""
    return f'"{c}"' if prefix == "pg" else c


class Database:
    def __init__(self, dialect: str = None, url: str = None):
        self.dialect = dialect or settings.db_dialect
        self.url = url or settings.database_url
        self._pg = None
        self._lock = asyncio.Lock()
        self._tables = _TABLES_POSTGRES if self.dialect == "postgres" else _TABLES_SQLITE
        self._ph = "%s" if self.dialect == "postgres" else "?"

    # -- lifecycle ----------------------------------------------------
    async def connect(self):
        if self.dialect == "postgres":
            import psycopg
            self._pg = await psycopg.AsyncConnection.connect(self.url)

    async def close(self):
        if self._pg is not None:
            await self._pg.close()
            self._pg = None

    def table(self, logical: str) -> str:
        return self._tables.get(logical, logical)

    # -- schema init --------------------------------------------------
    @staticmethod
    def _repo_root() -> Path:
        # Resolve repo root robustly: parent of the backend/ dir.
        here = Path(__file__).resolve()
        for parent in here.parents:
            if (parent / "db").exists() and (parent / "backend").exists():
                return parent
        return Path.cwd()

    async def initialize(self):
        root = self._repo_root()
        sql_path = (root / "db/migrations/001_create_schemas.sql"
                    if self.dialect == "postgres" else root / "db/demo_sqlite.sql")
        if sql_path.exists():
            await self.execute_script(sql_path.read_text(encoding="utf-8"))
            print(f"[db] initialized schema from {sql_path}")
        else:
            print(f"[db] WARNING: schema file not found at {sql_path}")

    # -- sqlite helpers ------------------------------------------------
    def _sqlite_path(self):
        raw = self.url.replace("sqlite:///", "").replace("sqlite://", "")
        p = Path(raw)
        if not p.is_absolute():
            p = self._repo_root() / p
        return p

    def _sqlite_conn(self):
        path = self._sqlite_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return conn

    # -- public API ----------------------------------------------------
    async def execute(self, query: str, params: Sequence = ()) -> Any:
        async with self._lock:
            if self.dialect == "postgres":
                cur = await self._pg.cursor()
                await cur.execute(query, tuple(params))
                await self._pg.commit()
                return cur
            return await asyncio.to_thread(self._sqlite_execute, query, tuple(params))

    def _sqlite_execute(self, query, params):
        conn = self._sqlite_conn()
        try:
            cur = conn.execute(query, params)
            conn.commit()
            return cur
        finally:
            conn.close()

    async def execute_script(self, sql: str):
        async with self._lock:
            if self.dialect == "postgres":
                cur = await self._pg.cursor()
                await cur.execute(sql)
                await self._pg.commit()
                return
            await asyncio.to_thread(self._sqlite_script, sql)

    def _sqlite_script(self, sql):
        conn = self._sqlite_conn()
        try:
            conn.executescript(sql)
            conn.commit()
        finally:
            conn.close()

    async def fetch(self, query: str, params: Sequence = ()) -> list[dict]:
        if self.dialect == "postgres":
            cur = await self._pg.cursor()
            await cur.execute(query, tuple(params))
            cols = [c.name for c in cur.description] if cur.description else []
            rows = await cur.fetchall()
            return [dict(zip(cols, r)) for r in rows]
        return await asyncio.to_thread(self._sqlite_fetch, query, tuple(params))

    def _sqlite_fetch(self, query, params):
        conn = self._sqlite_conn()
        try:
            return [dict(r) for r in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    async def count(self, logical: str) -> int:
        rows = await self.fetch(f"SELECT COUNT(*) AS n FROM {self.table(logical)}")
        return int(rows[0]["n"]) if rows else 0

    async def upsert(self, logical: str, conflict_cols: list[str], data: dict[str, Any],
                     update_cols: list[str] | None = None) -> int:
        """Insert-or-update on conflict. Returns rowcount-ish int."""
        table = self.table(logical)
        cols = list(data.keys())
        placeholders = ", ".join([self._ph] * len(cols))
        collist = ", ".join(cols)
        vals = list(data.values())

        if self.dialect == "postgres":
            conflict = ", ".join(conflict_cols)
            updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in (update_cols or [c for c in cols if c not in conflict_cols]))
            query = (f"INSERT INTO {table} ({collist}) VALUES ({placeholders}) "
                     f"ON CONFLICT ({conflict}) DO UPDATE SET {updates}")
        else:  # sqlite
            conflict = ", ".join(conflict_cols)
            updates = ", ".join(f"{c}=excluded.{c}" for c in (update_cols or [c for c in cols if c not in conflict_cols]))
            query = (f"INSERT INTO {table} ({collist}) VALUES ({placeholders}) "
                     f"ON CONFLICT({conflict}) DO UPDATE SET {updates}")

        cur = await self.execute(query, vals)
        try:
            return cur.rowcount
        except Exception:
            return len(vals)
