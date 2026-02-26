"""Fundamental analysis: PE/PB valuation, ROE quality, revenue/profit growth, margins."""

import logging
from decimal import Decimal

from .base import AnalyzerBase
from .types import AnalysisResult, Signal
from ..models import FinancialReport

logger = logging.getLogger(__name__)

# Fields that contribute to confidence when non-null.
_CONFIDENCE_FIELDS = [
    "pe_ratio",
    "pb_ratio",
    "roe",
    "revenue",
    "net_profit",
    "gross_margin",
    "debt_ratio",
]


class FundamentalAnalyzer(AnalyzerBase):
    """Fundamental analysis (PE/PB valuation, ROE, growth, margins).

    Scoring components (each 0-100):
      - Valuation  (30%): PE ratio + PB bonus
      - Quality    (25%): ROE assessment
      - Growth     (25%): Revenue and net-profit growth trends
      - Margins    (20%): Gross margin + debt-ratio adjustment

    Final score is a weighted average clamped to 0-100.
    Score > 70 -> BUY, < 30 -> SELL, else HOLD.
    """

    name = "fundamental"
    description = "Fundamental analysis (PE/PB valuation, ROE, growth, margins)"

    WEIGHTS = {
        "valuation": 0.30,
        "quality": 0.25,
        "growth": 0.25,
        "margins": 0.20,
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        reports = list(
            FinancialReport.objects.filter(stock_id=stock_code)
            .order_by("-period")[:4]
        )

        if not reports:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="No financial report data available",
            )

        latest = reports[0]

        # Component scores.
        valuation_score = self._score_valuation(latest)
        quality_score = self._score_quality(latest)
        growth_score = self._score_growth(reports)
        margins_score = self._score_margins(latest)

        # Weighted combination.
        component_scores = {
            "valuation": valuation_score,
            "quality": quality_score,
            "growth": growth_score,
            "margins": margins_score,
        }
        final_score = sum(
            component_scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS
        )
        final_score = round(max(0.0, min(100.0, final_score)), 2)

        # Signal.
        if final_score > 70:
            signal = Signal.BUY
        elif final_score < 30:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        # Confidence: proportion of key fields that are non-null in the
        # latest report.
        confidence = self._compute_confidence(reports)

        explanation = self._build_explanation(component_scores, signal)

        return AnalysisResult(
            score=final_score,
            signal=signal,
            confidence=confidence,
            explanation=explanation,
            details={"component_scores": component_scores},
        )

    # ------------------------------------------------------------------
    # Valuation (30%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_valuation(report: FinancialReport) -> float:
        pe = report.pe_ratio
        pb = report.pb_ratio

        if pe is None:
            score = 50.0
        else:
            pe_f = float(pe)
            if pe_f < 10:
                score = 90.0
            elif pe_f < 15:
                score = 75.0
            elif pe_f < 25:
                score = 55.0
            elif pe_f < 40:
                score = 35.0
            else:
                score = 15.0

        # PB bonus.
        if pb is not None and float(pb) < 1:
            score += 10.0

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Quality (25%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_quality(report: FinancialReport) -> float:
        roe = report.roe
        if roe is None:
            return 50.0

        roe_f = float(roe)
        if roe_f > 20:
            return 90.0
        elif roe_f > 15:
            return 75.0
        elif roe_f > 10:
            return 55.0
        elif roe_f > 5:
            return 35.0
        else:
            return 15.0

    # ------------------------------------------------------------------
    # Growth (25%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_growth(reports: list) -> float:
        """Compare the latest 2 periods' revenue and net_profit.

        If only one report exists, return a neutral score.
        """
        if len(reports) < 2:
            return 50.0

        latest = reports[0]
        previous = reports[1]

        rev_score = FundamentalAnalyzer._growth_sub_score(
            latest.revenue, previous.revenue
        )
        profit_score = FundamentalAnalyzer._growth_sub_score(
            latest.net_profit, previous.net_profit
        )

        return (rev_score + profit_score) / 2.0

    @staticmethod
    def _growth_sub_score(
        current_val: Decimal | None,
        previous_val: Decimal | None,
    ) -> float:
        if current_val is None or previous_val is None:
            return 50.0
        if previous_val == 0:
            return 50.0

        growth = float((current_val - previous_val) / abs(previous_val)) * 100

        if growth > 20:
            return 85.0
        elif growth > 10:
            return 70.0
        elif growth > 0:
            return 50.0
        else:
            return 25.0

    # ------------------------------------------------------------------
    # Margins (20%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_margins(report: FinancialReport) -> float:
        gm = report.gross_margin
        dr = report.debt_ratio

        if gm is None:
            score = 50.0
        else:
            gm_f = float(gm)
            if gm_f > 50:
                score = 85.0
            elif gm_f > 30:
                score = 70.0
            elif gm_f > 15:
                score = 50.0
            else:
                score = 30.0

        # Debt ratio adjustment.
        if dr is not None:
            dr_f = float(dr)
            if dr_f < 40:
                score += 10.0
            elif dr_f > 70:
                score -= 10.0

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence(reports: list) -> float:
        """Confidence = proportion of key fields that are non-null across reports."""
        total_fields = 0
        non_null = 0
        for report in reports:
            for field_name in _CONFIDENCE_FIELDS:
                total_fields += 1
                if getattr(report, field_name) is not None:
                    non_null += 1

        if total_fields == 0:
            return 0.0

        return round(min(1.0, non_null / total_fields), 2)

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
            prefix = "Bullish fundamentals"
        elif signal == Signal.SELL:
            prefix = "Bearish fundamentals"
        else:
            prefix = "Mixed fundamentals"

        detail = "; ".join(parts[:3]) if parts else "neutral across dimensions"
        return f"{prefix}: {detail}"
