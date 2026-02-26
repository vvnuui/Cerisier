"""AI-enhanced analyzer using LLM for factor scoring and report generation."""

import logging

from .base import AnalyzerBase
from .types import AnalysisResult, Signal

logger = logging.getLogger(__name__)


class AIAnalyzer(AnalyzerBase):
    """AI-enhanced stock analysis using LLM for factor adjustment.

    Uses AIService.score_factors() to get AI-adjusted scores based on
    multi-factor analysis results. Falls back gracefully when AI is
    unavailable or budget is exceeded.

    Scoring:
      - Calls AIService.score_factors() with available factor data
      - Maps AI's adjusted_score (0-100) to signal
      - Confidence based on AI response quality

    Score >= 70 -> BUY, <= 30 -> SELL, else HOLD.
    """

    name = "ai"
    description = "AI-enhanced analysis using LLM for factor scoring"

    def __init__(self, provider: str = "deepseek"):
        self.provider = provider

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        """Analyze a stock using AI-enhanced factor scoring.

        Args:
            stock_code: Stock code
            **kwargs: Optional 'factor_data' dict with existing analysis results.
                      If not provided, gathers basic data from models.

        Returns:
            AnalysisResult with AI-adjusted score
        """
        from ..ai.service import AIService, AIServiceError
        from ..models import StockBasic

        # Get stock info
        try:
            stock = StockBasic.objects.get(code=stock_code)
            stock_name = stock.name
        except StockBasic.DoesNotExist:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Stock not found for AI analysis",
            )

        # Build factor data if not provided
        factor_data = kwargs.get("factor_data")
        if factor_data is None:
            factor_data = self._gather_factor_data(stock_code)

        # Call AI service
        try:
            service = AIService(provider=self.provider)
            ai_result = service.score_factors(stock_code, stock_name, factor_data)
        except AIServiceError as e:
            logger.warning(f"AI service unavailable for {stock_code}: {e}")
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation=f"AI analysis unavailable: {str(e)}",
                details={"error": str(e)},
            )

        # Parse AI response
        adjusted_score = float(ai_result.get("adjusted_score", 50))
        adjusted_score = max(0.0, min(100.0, adjusted_score))

        reasoning = ai_result.get("reasoning", "")
        risk_factors = ai_result.get("risk_factors", [])
        catalysts = ai_result.get("catalysts", [])

        # Signal from score
        if adjusted_score >= 70:
            signal = Signal.BUY
        elif adjusted_score <= 30:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        # Confidence: AI responses have moderate confidence
        confidence = 0.7 if reasoning else 0.3

        explanation = f"AI analysis: {reasoning}" if reasoning else "AI analysis complete"

        return AnalysisResult(
            score=round(adjusted_score, 2),
            signal=signal,
            confidence=confidence,
            explanation=explanation,
            details={
                "adjusted_score": adjusted_score,
                "reasoning": reasoning,
                "risk_factors": risk_factors,
                "catalysts": catalysts,
                "provider": self.provider,
            },
        )

    @staticmethod
    def _gather_factor_data(stock_code: str) -> dict:
        """Gather basic factor data from available models."""
        from ..models import FinancialReport, KlineData

        data = {"stock_code": stock_code}

        # Latest financial data
        report = (
            FinancialReport.objects.filter(stock_id=stock_code)
            .order_by("-period")
            .first()
        )
        if report:
            data["financial"] = {
                "period": report.period,
                "pe_ratio": float(report.pe_ratio) if report.pe_ratio else None,
                "pb_ratio": float(report.pb_ratio) if report.pb_ratio else None,
                "roe": float(report.roe) if report.roe else None,
                "revenue": float(report.revenue) if report.revenue else None,
                "net_profit": float(report.net_profit) if report.net_profit else None,
            }

        # Recent price data
        klines = list(
            KlineData.objects.filter(stock_id=stock_code)
            .order_by("-date")[:5]
        )
        if klines:
            data["recent_prices"] = [
                {
                    "date": k.date.isoformat(),
                    "close": float(k.close),
                    "volume": k.volume,
                    "change_pct": float(k.change_pct) if k.change_pct else None,
                }
                for k in klines
            ]

        return data

    def generate_report(self, stock_code: str, analysis_data: dict) -> dict:
        """Generate a comprehensive AI report (not part of AnalyzerBase).

        This is a supplementary method for generating detailed reports.

        Args:
            stock_code: Stock code
            analysis_data: Full analysis data dict

        Returns:
            Dict with report sections, or error dict on failure
        """
        from ..ai.service import AIService, AIServiceError
        from ..models import StockBasic

        try:
            stock = StockBasic.objects.get(code=stock_code)
            stock_name = stock.name
        except StockBasic.DoesNotExist:
            return {"error": "Stock not found"}

        try:
            service = AIService(provider=self.provider)
            return service.generate_report(stock_code, stock_name, analysis_data)
        except AIServiceError as e:
            logger.warning(f"Report generation failed for {stock_code}: {e}")
            return {"error": str(e)}
