"""Money-flow analysis: main force net inflow, big-order ratio, retail divergence, momentum."""

import logging

from .base import AnalyzerBase
from .types import AnalysisResult, Signal
from ..models import MoneyFlow

logger = logging.getLogger(__name__)


class MoneyFlowAnalyzer(AnalyzerBase):
    """Capital-flow pattern analysis from MoneyFlow data.

    Scoring components (each 0-100):
      - main_net_trend (30%): Main force net inflow trend over recent days
      - big_order_ratio (25%): Ratio of huge+big net vs total absolute flow
      - retail_flow     (25%): Retail (small+mid) flow divergence vs main force
      - flow_momentum   (20%): Acceleration of main_net (5d avg vs 10d avg)

    Final score is a weighted average clamped to 0-100.
    Score >= 70 -> BUY, <= 30 -> SELL, else HOLD.
    """

    name = "money_flow"
    description = "Capital flow pattern analysis (main force, big orders, retail divergence)"

    WEIGHTS = {
        "main_net_trend": 0.30,
        "big_order_ratio": 0.25,
        "retail_flow": 0.25,
        "flow_momentum": 0.20,
    }

    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        flows = list(
            MoneyFlow.objects.filter(stock_id=stock_code)
            .order_by("-date")[: self.lookback_days]
        )

        if len(flows) < 5:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient money-flow data for analysis",
            )

        # Reverse so oldest first.
        flows = list(reversed(flows))

        component_scores = {
            "main_net_trend": self._score_main_net_trend(flows),
            "big_order_ratio": self._score_big_order_ratio(flows),
            "retail_flow": self._score_retail_flow(flows),
            "flow_momentum": self._score_flow_momentum(flows),
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

        confidence = self._compute_confidence(flows)
        explanation = self._build_explanation(component_scores, signal)

        return AnalysisResult(
            score=final_score,
            signal=signal,
            confidence=confidence,
            explanation=explanation,
            details={"component_scores": component_scores},
        )

    # ------------------------------------------------------------------
    # Main-net trend (30%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_main_net_trend(flows: list) -> float:
        """Positive main_net sum over recent days is bullish."""
        main_nets = [float(f.main_net) for f in flows]
        total = sum(main_nets)
        avg = total / len(main_nets) if main_nets else 0.0

        score = 50.0
        # Normalize: a strong daily avg inflow shifts score significantly.
        if avg > 0:
            score += min(40.0, avg / 1_000_000 * 10)
        else:
            score -= min(40.0, abs(avg) / 1_000_000 * 10)

        # Extra: count of positive days.
        positive_days = sum(1 for m in main_nets if m > 0)
        ratio = positive_days / len(main_nets)
        if ratio > 0.7:
            score += 10
        elif ratio < 0.3:
            score -= 10

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Big-order ratio (25%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_big_order_ratio(flows: list) -> float:
        """Ratio of (huge_net + big_net) to total absolute flow."""
        total_big = sum(float(f.huge_net) + float(f.big_net) for f in flows)
        total_abs = sum(
            abs(float(f.huge_net))
            + abs(float(f.big_net))
            + abs(float(f.mid_net))
            + abs(float(f.small_net))
            for f in flows
        )

        if total_abs == 0:
            return 50.0

        ratio = total_big / total_abs  # Range roughly -1 to +1.

        score = 50.0
        # Positive ratio means institutional net buying dominates.
        score += ratio * 40

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Retail flow (25%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_retail_flow(flows: list) -> float:
        """Retail selling while main force buying = bullish divergence."""
        main_total = sum(float(f.main_net) for f in flows)
        retail_total = sum(float(f.small_net) + float(f.mid_net) for f in flows)

        score = 50.0

        # Bullish divergence: main buying, retail selling.
        if main_total > 0 and retail_total < 0:
            score += 25
        # Bearish divergence: main selling, retail buying.
        elif main_total < 0 and retail_total > 0:
            score -= 25
        # Consensus buying.
        elif main_total > 0 and retail_total > 0:
            score += 10
        # Consensus selling.
        elif main_total < 0 and retail_total < 0:
            score -= 10

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Flow momentum (20%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_flow_momentum(flows: list) -> float:
        """Acceleration: recent 5d main_net avg vs full-period avg."""
        main_nets = [float(f.main_net) for f in flows]

        if len(main_nets) < 5:
            return 50.0

        recent_avg = sum(main_nets[-5:]) / 5
        full_avg = sum(main_nets) / len(main_nets)

        score = 50.0

        if full_avg == 0:
            # Just use recent avg direction.
            if recent_avg > 0:
                score += 15
            elif recent_avg < 0:
                score -= 15
        else:
            # Acceleration = recent exceeds overall.
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
    def _compute_confidence(flows: list) -> float:
        """Confidence based on data availability (more days = higher)."""
        if len(flows) >= 15:
            return 0.9
        elif len(flows) >= 10:
            return 0.7
        elif len(flows) >= 5:
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
            prefix = "Bullish capital flow"
        elif signal == Signal.SELL:
            prefix = "Bearish capital flow"
        else:
            prefix = "Mixed capital flow"

        detail = "; ".join(parts[:3]) if parts else "neutral across flow dimensions"
        return f"{prefix}: {detail}"
