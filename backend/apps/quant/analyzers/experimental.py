"""Experimental / stub analyzers: game theory, behavior finance, macro."""

import logging
from decimal import Decimal

from .base import AnalyzerBase
from .types import AnalysisResult, Signal
from ..models import KlineData

logger = logging.getLogger(__name__)


class GameTheoryAnalyzer(AnalyzerBase):
    """Placeholder game-theory analyzer using volume-price divergence patterns.

    Analyzes the relationship between volume and price to infer
    institutional vs retail positioning.
    """

    name = "game_theory"
    description = "Game theory analysis (volume-price divergence patterns)"

    WEIGHTS = {
        "volume_price_divergence": 0.50,
        "volume_trend": 0.50,
    }

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        klines = list(
            KlineData.objects.filter(stock_id=stock_code)
            .order_by("-date")[: self.lookback_days]
        )

        if len(klines) < 10:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient data for game theory analysis",
            )

        # Reverse so oldest first.
        klines = list(reversed(klines))

        component_scores = {
            "volume_price_divergence": self._score_volume_price_divergence(klines),
            "volume_trend": self._score_volume_trend(klines),
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

        confidence = min(1.0, len(klines) / self.lookback_days * 0.5)

        return AnalysisResult(
            score=final_score,
            signal=signal,
            confidence=round(confidence, 2),
            explanation=f"Game theory analysis: score={final_score:.0f}",
            details={"component_scores": component_scores},
        )

    @staticmethod
    def _score_volume_price_divergence(klines: list) -> float:
        """Price up + volume down or price down + volume up = divergence."""
        if len(klines) < 5:
            return 50.0

        recent = klines[-5:]
        price_change = float(recent[-1].close) - float(recent[0].close)
        vol_first = sum(k.volume for k in recent[:2]) / 2
        vol_last = sum(k.volume for k in recent[-2:]) / 2

        score = 50.0

        if vol_first == 0:
            return 50.0

        vol_change = (vol_last - vol_first) / vol_first

        # Price up + volume up = bullish confirmation.
        if price_change > 0 and vol_change > 0.1:
            score += 20
        # Price up + volume down = weakening (bearish divergence).
        elif price_change > 0 and vol_change < -0.1:
            score -= 10
        # Price down + volume up = capitulation / potential reversal.
        elif price_change < 0 and vol_change > 0.1:
            score += 5
        # Price down + volume down = bearish continuation.
        elif price_change < 0 and vol_change < -0.1:
            score -= 15

        return max(0.0, min(100.0, score))

    @staticmethod
    def _score_volume_trend(klines: list) -> float:
        """Rising volume trend is generally a signal of interest."""
        if len(klines) < 10:
            return 50.0

        first_half = klines[: len(klines) // 2]
        second_half = klines[len(klines) // 2 :]

        avg_first = sum(k.volume for k in first_half) / len(first_half)
        avg_second = sum(k.volume for k in second_half) / len(second_half)

        score = 50.0

        if avg_first == 0:
            return 50.0

        ratio = avg_second / avg_first

        # Rising volume with price context.
        price_change = float(klines[-1].close) - float(klines[0].close)

        if ratio > 1.3 and price_change > 0:
            score += 20
        elif ratio > 1.1 and price_change > 0:
            score += 10
        elif ratio > 1.3 and price_change < 0:
            score -= 15
        elif ratio < 0.7:
            score -= 5  # Declining interest.

        return max(0.0, min(100.0, score))


class BehaviorFinanceAnalyzer(AnalyzerBase):
    """Detects behavioral biases from price patterns (overreaction, anchoring).

    Uses KlineData to detect:
    - Overreaction: sharp price moves that may revert
    - Anchoring: range-bound trading after big moves
    """

    name = "behavior_finance"
    description = "Behavioral finance analysis (overreaction, anchoring patterns)"

    WEIGHTS = {
        "overreaction": 0.50,
        "anchoring": 0.50,
    }

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        klines = list(
            KlineData.objects.filter(stock_id=stock_code)
            .order_by("-date")[: self.lookback_days]
        )

        if len(klines) < 10:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient data for behavior finance analysis",
            )

        # Reverse so oldest first.
        klines = list(reversed(klines))

        component_scores = {
            "overreaction": self._score_overreaction(klines),
            "anchoring": self._score_anchoring(klines),
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

        confidence = min(1.0, len(klines) / self.lookback_days * 0.4)

        return AnalysisResult(
            score=final_score,
            signal=signal,
            confidence=round(confidence, 2),
            explanation=f"Behavior finance analysis: score={final_score:.0f}",
            details={"component_scores": component_scores},
        )

    @staticmethod
    def _score_overreaction(klines: list) -> float:
        """Detect sharp recent moves that may revert (contrarian)."""
        if len(klines) < 5:
            return 50.0

        recent = klines[-5:]
        total_change_pct = 0.0
        for i in range(1, len(recent)):
            prev_close = float(recent[i - 1].close)
            if prev_close != 0:
                total_change_pct += (
                    (float(recent[i].close) - prev_close) / prev_close * 100
                )

        score = 50.0

        # Sharp drop = potential overreaction (buy opportunity).
        if total_change_pct < -10:
            score += 25
        elif total_change_pct < -5:
            score += 15
        # Sharp rise = potential overreaction (sell opportunity).
        elif total_change_pct > 10:
            score -= 25
        elif total_change_pct > 5:
            score -= 15

        return max(0.0, min(100.0, score))

    @staticmethod
    def _score_anchoring(klines: list) -> float:
        """Detect range-bound trading after a big move (anchoring bias)."""
        if len(klines) < 10:
            return 50.0

        # Check if earlier part had big move, and recent part is range-bound.
        early = klines[: len(klines) // 2]
        recent = klines[len(klines) // 2 :]

        early_range = max(float(k.high) for k in early) - min(
            float(k.low) for k in early
        )
        recent_range = max(float(k.high) for k in recent) - min(
            float(k.low) for k in recent
        )

        avg_price = float(klines[-1].close)
        if avg_price == 0:
            return 50.0

        early_range_pct = early_range / avg_price * 100
        recent_range_pct = recent_range / avg_price * 100

        score = 50.0

        # Narrowing range after big move = anchoring, potential breakout.
        if early_range_pct > 10 and recent_range_pct < 5:
            # Direction depends on where price is relative to range.
            mid_price = (
                max(float(k.high) for k in recent)
                + min(float(k.low) for k in recent)
            ) / 2
            if float(klines[-1].close) > mid_price:
                score += 15  # Near top of range, likely breakout up.
            else:
                score -= 10  # Near bottom, likely breakout down.

        return max(0.0, min(100.0, score))


class MacroAnalyzer(AnalyzerBase):
    """Placeholder macro analyzer returning neutral results.

    Requires external data integration (macro-economic indicators, interest
    rates, policy signals, etc.) which is not yet implemented.
    """

    name = "macro"
    description = "Macro environment analysis (placeholder - requires external data)"

    WEIGHTS = {}

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        return AnalysisResult(
            score=50.0,
            signal=Signal.HOLD,
            confidence=0.1,
            explanation="Macro analysis requires external data integration",
            details={"status": "placeholder"},
        )
