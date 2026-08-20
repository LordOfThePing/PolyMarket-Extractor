"""Analytics engine.

Computes the headline deliverable: "Most Profitable Predictions" ranked
by category, using ROI, win rate, volume and liquidity.
"""
from __future__ import annotations

from ..db.database import Database


class AnalyticsEngine:
    def __init__(self, db: Database):
        self.db = db

    # -- resolved real performance (winrate/ROI per category) ----------
    async def category_performance(self) -> list[dict]:
        """Compute win rate + ROI per category from resolved predictions."""
        query = """
            SELECT rm.category,
                   COUNT(*) as total_markets,
                   SUM(CASE WHEN rp.is_correct = 1 THEN 1 ELSE 0 END) as win_count,
                   SUM(CASE WHEN rp.is_correct = 0 THEN 1 ELSE 0 END) as loss_count,
                   ROUND(AVG(CASE WHEN rp.predicted_prob IS NOT NULL THEN rp.predicted_prob END),2) as avg_pred_prob
            FROM resolved.predictions rp
            JOIN resolved.markets rm ON rm.id = rp.market_id
            GROUP BY rm.category
        """
        # SQLite fallback uses the flat table names; run a portable query.
        if self.db.dialect == "sqlite":
            query = query.replace("resolved.predictions", "resolved_predictions")                          .replace("resolved.markets", "resolved_markets")                          .replace("rp.", "rp.").replace("rm.", "rm.")
        rows = await self.db.fetch(query)
        out = []
        for r in rows:
            total = int(r.get("total_markets") or 0)
            win_count = int(r.get("win_count") or 0)
            loss_count = int(r.get("loss_count") or 0)
            win_rate = round(win_count / total * 100, 2) if total else 0.0
            # simplistic ROI: payouts on winning YES at avg prob, stake 100
            avg_prob = float(r.get("avg_pred_prob") or 0) / 100.0 if r.get("avg_pred_prob") else 0.0
            notional = total * 100
            collected = (100.0 * win_count) - notional
            roi = round(collected / max(notional, 1) * 100, 2)
            out.append({
                "category": r["category"],
                "total_markets": total,
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate_pct": win_rate,
                "roi_pct": roi,
            })
        out.sort(key=lambda x: x["roi_pct"], reverse=True)
        return out

    # -- most profitable predictions (ranked) --------------------------
    async def most_profitable(self, category: str | None = None, limit: int = 10) -> list[dict]:
        """Rank predictions by profitability -> the headline deliverable."""
        query = """
            SELECT rm.category, rm.question, rp.outcome, rp.predicted_prob,
                   rp.resolved_prob, rp.is_correct,
                   (CASE WHEN rp.is_correct = 1 THEN (100.0 - rp.predicted_prob)
                         ELSE rp.predicted_prob END) AS implied_profit
            FROM resolved.predictions rp
            JOIN resolved.markets rm ON rm.id = rp.market_id
            WHERE rp.predicted_prob IS NOT NULL
            ORDER BY implied_profit DESC
        """
        params: tuple = ()
        if self.db.dialect == "sqlite":
            query = query.replace("resolved.predictions", "resolved_predictions")                          .replace("resolved.markets", "resolved_markets")
        if category:
            query = query.replace("WHERE rp.predicted_prob IS NOT NULL",
                                  "WHERE rp.predicted_prob IS NOT NULL AND rm.category = '" + category + "'")
        rows = await self.db.fetch(query, params)
        return rows[:limit]

    # -- mock backtest results (mock schema) ---------------------------
    async def mock_runs(self) -> list[dict]:
        query = self._portable("SELECT * FROM {mock.runs} ORDER BY started_at DESC LIMIT 20")
        return await self.db.fetch(query)

    def _portable(self, sql: str) -> str:
        if self.db.dialect == "sqlite":
            return sql.replace("{mock.runs}", "mock_runs")
        return sql.replace("{mock.runs}", "mock.runs")
