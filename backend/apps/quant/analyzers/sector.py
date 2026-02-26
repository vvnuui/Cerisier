"""Sector rotation analysis: sector momentum, sector flow, relative strength."""

import logging

from .base import AnalyzerBase
from .types import AnalysisResult, Signal
from ..models import KlineData, MoneyFlow, StockBasic

logger = logging.getLogger(__name__)


class SectorRotationAnalyzer(AnalyzerBase):
    """Sector-level performance analysis using KlineData aggregated by industry.

    Scoring components (each 0-100):
      - sector_momentum  (40%): Average return of stocks in same industry
      - sector_flow      (30%): Net money flow into the sector
      - relative_strength (30%): Stock's performance vs sector average

    Final score is a weighted average clamped to 0-100.
    Score >= 70 -> BUY, <= 30 -> SELL, else HOLD.
    """

    name = "sector_rotation"
    description = "Sector rotation analysis (sector momentum, flow, relative strength)"

    WEIGHTS = {
        "sector_momentum": 0.40,
        "sector_flow": 0.30,
        "relative_strength": 0.30,
    }

    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        # Look up the stock's industry.
        try:
            stock = StockBasic.objects.get(code=stock_code)
        except StockBasic.DoesNotExist:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Stock not found for sector analysis",
            )

        industry = stock.industry
        if not industry:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Stock has no industry classification",
            )

        # Find all stocks in the same industry.
        sector_stocks = list(
            StockBasic.objects.filter(
                industry=industry, is_active=True
            ).values_list("code", flat=True)
        )

        if len(sector_stocks) < 3:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient stocks in sector for analysis",
            )

        # Compute stock returns for the sector.
        stock_returns = self._compute_sector_returns(sector_stocks)

        if len(stock_returns) < 3:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient kline data in sector for analysis",
            )

        target_return = stock_returns.get(stock_code)

        component_scores = {
            "sector_momentum": self._score_sector_momentum(stock_returns),
            "sector_flow": self._score_sector_flow(sector_stocks),
            "relative_strength": self._score_relative_strength(
                target_return, stock_returns
            ),
        }

        final_score = sum(
            component_scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS
        )
        final_score = round(max(0.0, min(100.0, final_score)), 2)

        if final_score >= 70:
            signal = Signal.BUY
        elif final_score <= 30:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        confidence = self._compute_confidence(stock_returns, sector_stocks)
        explanation = self._build_explanation(component_scores, signal)

        return AnalysisResult(
            score=final_score,
            signal=signal,
            confidence=confidence,
            explanation=explanation,
            details={"component_scores": component_scores},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_sector_returns(self, stock_codes: list) -> dict:
        """Compute return % for each stock over the lookback period.

        Returns dict of {stock_code: return_pct}.
        Only includes stocks with at least 10 days of data.
        Uses a single batch query to avoid N+1 performance issues.
        """
        from django.db.models import Max, Min, Count

        # Determine the date cutoff via a single aggregate query.
        latest_date_row = (
            KlineData.objects.filter(stock_id__in=stock_codes)
            .order_by("-date")
            .values("date")
            .first()
        )
        if not latest_date_row:
            return {}

        # Fetch all klines for the sector in one query.
        all_klines = list(
            KlineData.objects.filter(stock_id__in=stock_codes)
            .order_by("stock_id", "-date")
        )

        # Group by stock and compute returns.
        from itertools import groupby
        from operator import attrgetter

        returns = {}
        for code, group in groupby(all_klines, key=attrgetter("stock_id")):
            klines = list(group)[: self.lookback_days]
            if len(klines) < 10:
                continue
            newest = float(klines[0].close)
            oldest = float(klines[-1].close)
            if oldest != 0:
                returns[code] = (newest - oldest) / oldest * 100
        return returns

    # ------------------------------------------------------------------
    # Sector momentum (40%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_sector_momentum(stock_returns: dict) -> float:
        """Average return of stocks in the sector."""
        if not stock_returns:
            return 50.0

        avg_return = sum(stock_returns.values()) / len(stock_returns)

        score = 50.0
        if avg_return > 10:
            score += 35
        elif avg_return > 5:
            score += 25
        elif avg_return > 2:
            score += 15
        elif avg_return > 0:
            score += 5
        elif avg_return > -2:
            score -= 5
        elif avg_return > -5:
            score -= 15
        elif avg_return > -10:
            score -= 25
        else:
            score -= 35

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Sector flow (30%)
    # ------------------------------------------------------------------

    def _score_sector_flow(self, stock_codes: list) -> float:
        """Sum of main_net for all stocks in the sector over lookback period.

        Uses a single batch query to avoid N+1 performance issues.
        """
        from django.db.models import Avg

        # Batch query: fetch all money flow records for the sector at once.
        all_flows = MoneyFlow.objects.filter(stock_id__in=stock_codes).order_by(
            "stock_id", "-date"
        )

        total_flow = 0.0
        count = 0
        from itertools import groupby
        from operator import attrgetter

        for code, group in groupby(all_flows, key=attrgetter("stock_id")):
            for f in list(group)[: self.lookback_days]:
                total_flow += float(f.main_net)
                count += 1

        if count == 0:
            return 50.0

        avg_flow = total_flow / count

        score = 50.0
        if avg_flow > 0:
            score += min(30.0, avg_flow / 1_000_000 * 10)
        else:
            score -= min(30.0, abs(avg_flow) / 1_000_000 * 10)

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Relative strength (30%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_relative_strength(
        target_return: float | None,
        stock_returns: dict,
    ) -> float:
        """Stock's performance vs sector average."""
        if target_return is None or not stock_returns:
            return 50.0

        avg_return = sum(stock_returns.values()) / len(stock_returns)
        diff = target_return - avg_return

        score = 50.0
        if diff > 10:
            score += 35
        elif diff > 5:
            score += 25
        elif diff > 2:
            score += 15
        elif diff > 0:
            score += 5
        elif diff > -2:
            score -= 5
        elif diff > -5:
            score -= 15
        elif diff > -10:
            score -= 25
        else:
            score -= 35

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence(stock_returns: dict, sector_stocks: list) -> float:
        """Confidence based on data coverage."""
        if not sector_stocks:
            return 0.0
        coverage = len(stock_returns) / len(sector_stocks)
        return round(min(1.0, coverage), 2)

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_explanation(scores: dict, signal: Signal) -> str:
        parts = []
        for name, s in sorted(
            scores.items(), key=lambda x: abs(x[1] - 50), reverse=True
        ):
            if s >= 65:
                parts.append(f"{name} bullish ({s:.0f})")
            elif s <= 35:
                parts.append(f"{name} bearish ({s:.0f})")

        if signal == Signal.BUY:
            prefix = "Bullish sector rotation"
        elif signal == Signal.SELL:
            prefix = "Bearish sector rotation"
        else:
            prefix = "Mixed sector signals"

        detail = "; ".join(parts[:3]) if parts else "neutral sector positioning"
        return f"{prefix}: {detail}"
