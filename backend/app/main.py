"""FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.database import Database

db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await db.initialize()
    yield
    await db.close()


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"service": settings.app_name, "version": settings.version, "status": "ok"}


@app.get("/health")
async def health():
    d = {"service": settings.app_name, "database": settings.db_dialect, "status": "ok"}
    try:
        d["live_markets"] = await db.count("live.markets")
        d["mock_trades"] = await db.count("mock.trades")
        d["resolved_markets"] = await db.count("resolved.markets")
    except Exception as e:  # noqa: BLE001
        d["status"] = "degraded"
        d["error"] = str(e)
    return d


def _register_routes():
    from .api import routes
    app.include_router(routes.router)


_register_routes()
