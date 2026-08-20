"""API routes: ingestion + analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..analytics.engine import AnalyticsEngine
from ..config import settings
from ..db.database import Database
from ..ingestors.clob_ingestor import ClobRestIngestor
from ..ingestors.gamma_ingestor import GammaIngestor
from ..ingestors.mock_ingestor import MockIngestor
from ..ingestors.resolved_ingestor import ResolvedIngestor

router = APIRouter(prefix="/api")


def _get_db() -> Database:
    from ..main import db
    return db


@router.post("/ingest/live", tags=["ingestion"])
async def ingest_live(limit: int = 50):
    db = _get_db()
    try:
        result = await GammaIngestor(db).run_once(limit=limit)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
    return result


@router.post("/ingest/mock", tags=["ingestion"])
async def ingest_mock(n_trades: int = 60, strategy: str = "confidence_threshold"):
    db = _get_db()
    return await MockIngestor(db).run_once(n_trades=n_trades, strategy=strategy)


@router.post("/ingest/resolved", tags=["ingestion"])
async def ingest_resolved(limit: int = 100):
    db = _get_db()
    return await ResolvedIngestor(db).run_once(limit=limit)


@router.get("/analytics/categories", tags=["analytics"])
async def category_performance():
    db = _get_db()
    return await AnalyticsEngine(db).category_performance()


@router.get("/analytics/most-profitable", tags=["analytics"])
async def most_profitable(category: str | None = None, limit: int = 10):
    db = _get_db()
    return await AnalyticsEngine(db).most_profitable(category=category, limit=limit)


@router.get("/analytics/mock-runs", tags=["analytics"])
async def mock_runs():
    db = _get_db()
    return await AnalyticsEngine(db).mock_runs()
