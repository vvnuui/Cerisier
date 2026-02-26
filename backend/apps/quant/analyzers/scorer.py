"""Multi-factor scorer that orchestrates all analyzers with style-dependent weights."""

import logging

from .ai_analyzer import AIAnalyzer
from .chip import ChipAnalyzer
from .experimental import BehaviorFinanceAnalyzer, GameTheoryAnalyzer, MacroAnalyzer
from .fundamental import FundamentalAnalyzer
from .money_flow import MoneyFlowAnalyzer
from .sector import SectorRotationAnalyzer
from .sentiment import SentimentAnalyzer
from .technical import TechnicalAnalyzer
from .types import Signal, TradingStyle

logger = logging.getLogger(__name__)


class MultiFactorScorer:
    """Orchestrates all analyzers and combines results with style-dependent weights.

    Each TradingStyle uses different weights:
    - ULTRA_SHORT: technical(40%), money_flow(25%), chip(15%), sentiment(10%),
                   game_theory(5%), behavior_finance(5%)
    - SWING: technical(25%), fundamental(10%), money_flow(15%), chip(15%),
             sentiment(10%), sector_rotation(10%), behavior_finance(5%), ai(10%)
    - MID_LONG: technical(10%), fundamental(25%), money_flow(10%), chip(10%),
                sentiment(5%), sector_rotation(10%), macro(5%), behavior_finance(5%),
                game_theory(5%), ai(15%)
    """

    STYLE_WEIGHTS = {
        TradingStyle.ULTRA_SHORT: {
            "technical": 0.40,
            "money_flow": 0.25,
            "chip": 0.15,
            "sentiment": 0.10,
            "game_theory": 0.05,
            "behavior_finance": 0.05,
        },
        TradingStyle.SWING: {
            "technical": 0.25,
            "fundamental": 0.10,
            "money_flow": 0.15,
            "chip": 0.15,
            "sentiment": 0.10,
            "sector_rotation": 0.10,
            "behavior_finance": 0.05,
            "ai": 0.10,
        },
        TradingStyle.MID_LONG: {
            "technical": 0.10,
            "fundamental": 0.25,
            "money_flow": 0.10,
            "chip": 0.10,
            "sentiment": 0.05,
            "sector_rotation": 0.10,
            "macro": 0.05,
            "behavior_finance": 0.05,
            "game_theory": 0.05,
            "ai": 0.15,
        },
    }

    def __init__(self, style: TradingStyle = TradingStyle.SWING):
        self.style = style
        self._analyzers = self._build_analyzers()

    # Registry of analyzer classes (not instances) to avoid eager instantiation.
    _ANALYZER_REGISTRY = {
        "technical": TechnicalAnalyzer,
        "fundamental": FundamentalAnalyzer,
        "money_flow": MoneyFlowAnalyzer,
        "chip": ChipAnalyzer,
        "sentiment": SentimentAnalyzer,
        "sector_rotation": SectorRotationAnalyzer,
        "game_theory": GameTheoryAnalyzer,
        "behavior_finance": BehaviorFinanceAnalyzer,
        "macro": MacroAnalyzer,
        "ai": AIAnalyzer,
    }

    def _build_analyzers(self) -> dict:
        """Build only the analyzer instances needed for the current style."""
        weights = self.STYLE_WEIGHTS[self.style]
        return {
            name: cls()
            for name, cls in self._ANALYZER_REGISTRY.items()
            if name in weights
        }

    def score(self, stock_code: str) -> dict:
        """Score a stock using all relevant analyzers.

        Returns:
            dict with keys:
                - final_score: float (0-100)
                - signal: Signal
                - confidence: float (0-1)
                - style: TradingStyle
                - explanation: str
                - analyzer_results: dict of {analyzer_name: AnalysisResult}
                - component_scores: dict of {analyzer_name: weighted_score}
        """
        weights = self.STYLE_WEIGHTS[self.style]
        results = {}

        for name, analyzer in self._analyzers.items():
            results[name] = analyzer.safe_analyze(stock_code)

        # Compute weighted score, adjusting by confidence
        total_weight = 0.0
        weighted_sum = 0.0
        component_scores = {}

        for name, result in results.items():
            w = weights.get(name, 0)
            # Confidence-adjusted weight: low confidence reduces influence
            effective_weight = w * max(0.1, result.confidence)
            weighted_sum += result.score * effective_weight
            total_weight += effective_weight
            component_scores[name] = round(result.score * w, 2)

        final_score = weighted_sum / total_weight if total_weight > 0 else 50.0
        final_score = round(max(0.0, min(100.0, final_score)), 2)

        # Signal from score
        if final_score >= 70:
            signal = Signal.BUY
        elif final_score <= 30:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        # Overall confidence: weighted average of per-analyzer confidence
        total_conf = sum(
            results[name].confidence * weights.get(name, 0) for name in results
        )
        total_w = sum(weights.get(name, 0) for name in results)
        confidence = round(total_conf / total_w if total_w > 0 else 0.0, 2)

        explanation = self._build_explanation(results, signal)

        return {
            "final_score": final_score,
            "signal": signal,
            "confidence": confidence,
            "style": self.style,
            "explanation": explanation,
            "analyzer_results": results,
            "component_scores": component_scores,
        }

    def _build_explanation(self, results: dict, signal: Signal) -> str:
        """Build explanation from top contributing factors."""
        parts = []
        for name, result in sorted(
            results.items(), key=lambda x: abs(x[1].score - 50), reverse=True
        ):
            if result.score >= 65:
                parts.append(f"{name} bullish ({result.score:.0f})")
            elif result.score <= 35:
                parts.append(f"{name} bearish ({result.score:.0f})")

        if signal == Signal.BUY:
            prefix = "Multi-factor bullish"
        elif signal == Signal.SELL:
            prefix = "Multi-factor bearish"
        else:
            prefix = "Multi-factor mixed"

        detail = "; ".join(parts[:3]) if parts else "neutral across all factors"
        return f"{prefix} ({self.style.value}): {detail}"
