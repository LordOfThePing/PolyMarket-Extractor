"""Pydantic response models."""
from pydantic import BaseModel


class SourceResult(BaseModel):
    source: str
    rows_inserted: int = 0
    detail: dict = {}


class CategoryPerformance(BaseModel):
    category: str
    total_markets: int
    win_count: int
    loss_count: int
    win_rate_pct: float
    roi_pct: float


class MostProfitableRow(BaseModel):
    category: str
    question: str
    outcome: str
    predicted_prob: float | None
    resolved_prob: float | None
    is_correct: int | None
    implied_profit: float | None


class PipelineRun(BaseModel):
    live: dict = {}
    mock: dict = {}
    resolved: dict = {}
