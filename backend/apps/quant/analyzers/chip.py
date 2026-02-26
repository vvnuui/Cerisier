"""Chip / margin-trading analysis: margin trend, short pressure, leverage ratio, momentum."""

import logging

from .base import AnalyzerBase
from .types import AnalysisResult, Signal
from ..models import MarginData

logger = logging.getLogger(__name__)


class ChipAnalyzer(AnalyzerBase):
    """Margin-trading (chips/leverage) sentiment analysis from MarginData.

    Scoring components (each 0-100):
      - margin_trend    (35%): Margin balance trend (increasing = bullish leveraged buying)
      - short_pressure  (25%): Short balance changes (decreasing = bullish, short covering)
      - leverage_ratio  (20%): margin_buy vs margin_repay ratio (buy > repay = bullish)
      - balance_momentum(20%): Acceleration of margin balance changes

    Final score is a weighted average clamped to 0-100.
    Score >= 70 -> BUY, <= 30 -> SELL, else HOLD.
    """

    name = "chip"
    description = "Margin trading / chip analysis (margin trend, short pressure, leverage)"

    WEIGHTS = {
        "margin_trend": 0.35,
        "short_pressure": 0.25,
        "leverage_ratio": 0.20,
        "balance_momentum": 0.20,
    }

    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        records = list(
            MarginData.objects.filter(stock_id=stock_code)
            .order_by("-date")[: self.lookback_days]
        )

        if len(records) < 5:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient margin data for chip analysis",
            )

        # Reverse so oldest first.
        records = list(reversed(records))

        component_scores = {
            "margin_trend": self._score_margin_trend(records),
            "short_pressure": self._score_short_pressure(records),
            "leverage_ratio": self._score_leverage_ratio(records),
            "balance_momentum": self._score_balance_momentum(records),
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

        confidence = self._compute_confidence(records)
        explanation = self._build_explanation(component_scores, signal)

        return AnalysisResult(
            score=final_score,
            signal=signal,
            confidence=confidence,
            explanation=explanation,
            details={"component_scores": component_scores},
        )

    # ------------------------------------------------------------------
    # Margin trend (35%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_margin_trend(records: list) -> float:
        """Margin balance trending up = bullish leveraged buying."""
        balances = [float(r.margin_balance) for r in records]
        if len(balances) < 2:
            return 50.0

        first_half = balances[: len(balances) // 2]
        second_half = balances[len(balances) // 2 :]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        score = 50.0

        if avg_first == 0:
            return 50.0

        change_pct = (avg_second - avg_first) / abs(avg_first) * 100

        if change_pct > 5:
            score += 30
        elif change_pct > 2:
            score += 20
        elif change_pct > 0:
            score += 10
        elif change_pct > -2:
            score -= 10
        elif change_pct > -5:
            score -= 20
        else:
            score -= 30

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Short pressure (25%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_short_pressure(records: list) -> float:
        """Decreasing short balance = bullish (short covering)."""
        shorts = [float(r.short_balance) for r in records]
        if len(shorts) < 2:
            return 50.0

        first_half = shorts[: len(shorts) // 2]
        second_half = shorts[len(shorts) // 2 :]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        score = 50.0

        if avg_first == 0:
            return 50.0

        change_pct = (avg_second - avg_first) / abs(avg_first) * 100

        # Decreasing shorts is bullish.
        if change_pct < -5:
            score += 30
        elif change_pct < -2:
            score += 20
        elif change_pct < 0:
            score += 10
        elif change_pct < 2:
            score -= 10
        elif change_pct < 5:
            score -= 20
        else:
            score -= 30

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Leverage ratio (20%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_leverage_ratio(records: list) -> float:
        """margin_buy vs margin_repay: buy > repay = bullish."""
        total_buy = sum(float(r.margin_buy) for r in records)
        total_repay = sum(float(r.margin_repay) for r in records)

        if total_repay == 0 and total_buy == 0:
            return 50.0

        score = 50.0

        if total_repay == 0:
            # All buying, no repay.
            score += 30
        else:
            ratio = total_buy / total_repay
            if ratio > 1.3:
                score += 30
            elif ratio > 1.1:
                score += 20
            elif ratio > 1.0:
                score += 10
            elif ratio > 0.9:
                score -= 10
            elif ratio > 0.7:
                score -= 20
            else:
                score -= 30

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Balance momentum (20%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_balance_momentum(records: list) -> float:
        """Acceleration of margin balance changes (recent 5d vs full period)."""
        balances = [float(r.margin_balance) for r in records]
        if len(balances) < 5:
            return 50.0

        # Daily changes.
        changes = [balances[i] - balances[i - 1] for i in range(1, len(balances))]
        if not changes:
            return 50.0

        recent_avg = sum(changes[-5:]) / min(5, len(changes[-5:]))
        full_avg = sum(changes) / len(changes)

        score = 50.0

        # Accelerating margin increase is bullish.
        if recent_avg > full_avg and recent_avg > 0:
            score += 25
        elif recent_avg < full_avg and recent_avg < 0:
            score -= 25
        elif recent_avg > full_avg:
            score += 10
        elif recent_avg < full_avg:
            score -= 10

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence(records: list) -> float:
        """Confidence based on data availability."""
        if len(records) >= 15:
            return 0.9
        elif len(records) >= 10:
            return 0.7
        elif len(records) >= 5:
            return 0.5
        return 0.0

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
            prefix = "Bullish chip/margin signals"
        elif signal == Signal.SELL:
            prefix = "Bearish chip/margin signals"
        else:
            prefix = "Mixed chip/margin signals"

        detail = "; ".join(parts[:3]) if parts else "neutral across margin dimensions"
        return f"{prefix}: {detail}"
