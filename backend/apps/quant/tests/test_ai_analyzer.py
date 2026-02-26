"""Tests for AIAnalyzer (AI-enhanced factor scoring)."""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.quant.analyzers.ai_analyzer import AIAnalyzer
from apps.quant.analyzers.types import AnalysisResult, Signal
from apps.quant.models import FinancialReport, KlineData, StockBasic


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stock(db):
    return StockBasic.objects.create(
        code="000001",
        name="平安银行",
        industry="银行",
        sector="金融",
        market="SZ",
        list_date=datetime.date(1991, 4, 3),
        is_active=True,
    )


# ---------------------------------------------------------------------------
# 1. test_ai_analyzer_name
# ---------------------------------------------------------------------------


class TestAIAnalyzerName:
    def test_ai_analyzer_name(self):
        """AIAnalyzer.name should be 'ai'."""
        analyzer = AIAnalyzer()
        assert analyzer.name == "ai"


# ---------------------------------------------------------------------------
# 2. test_ai_analyzer_buy_signal
# ---------------------------------------------------------------------------


class TestAIAnalyzerBuySignal:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_buy_signal(self, MockAIService, stock):
        """AI returning adjusted_score=80 should produce BUY signal."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 80,
            "reasoning": "Strong fundamentals",
            "risk_factors": ["market volatility"],
            "catalysts": ["earnings growth"],
        }

        analyzer = AIAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.BUY
        assert result.score >= 70


# ---------------------------------------------------------------------------
# 3. test_ai_analyzer_sell_signal
# ---------------------------------------------------------------------------


class TestAIAnalyzerSellSignal:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_sell_signal(self, MockAIService, stock):
        """AI returning adjusted_score=20 should produce SELL signal."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 20,
            "reasoning": "Weak outlook",
            "risk_factors": ["high debt"],
            "catalysts": [],
        }

        analyzer = AIAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.SELL
        assert result.score <= 30


# ---------------------------------------------------------------------------
# 4. test_ai_analyzer_hold_signal
# ---------------------------------------------------------------------------


class TestAIAnalyzerHoldSignal:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_hold_signal(self, MockAIService, stock):
        """AI returning adjusted_score=50 should produce HOLD signal."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 50,
            "reasoning": "Neutral outlook",
            "risk_factors": [],
            "catalysts": [],
        }

        analyzer = AIAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert 30 < result.score < 70


# ---------------------------------------------------------------------------
# 5. test_ai_analyzer_service_error_fallback
# ---------------------------------------------------------------------------


class TestAIAnalyzerServiceErrorFallback:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_service_error_fallback(self, MockAIService, stock):
        """AIServiceError should return neutral HOLD with confidence=0."""
        from apps.quant.ai.service import AIServiceError

        mock_service = MockAIService.return_value
        mock_service.score_factors.side_effect = AIServiceError("API unavailable")

        analyzer = AIAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.score == 50.0
        assert result.confidence == 0.0
        assert "unavailable" in result.explanation.lower()
        assert result.details["error"] == "API unavailable"


# ---------------------------------------------------------------------------
# 6. test_ai_analyzer_stock_not_found
# ---------------------------------------------------------------------------


class TestAIAnalyzerStockNotFound:
    @pytest.mark.django_db
    def test_ai_analyzer_stock_not_found(self):
        """Non-existent stock returns HOLD with confidence=0."""
        analyzer = AIAnalyzer()
        result = analyzer.analyze("NONEXISTENT_999")

        assert result.signal == Signal.HOLD
        assert result.score == 50.0
        assert result.confidence == 0.0
        assert "not found" in result.explanation.lower()


# ---------------------------------------------------------------------------
# 7. test_ai_analyzer_with_factor_data
# ---------------------------------------------------------------------------


class TestAIAnalyzerWithFactorData:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_with_factor_data(self, MockAIService, stock):
        """Passing factor_data in kwargs should use it directly."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 65,
            "reasoning": "Based on provided factors",
            "risk_factors": [],
            "catalysts": [],
        }

        factor_data = {"technical": 70, "fundamental": 60}
        analyzer = AIAnalyzer()
        result = analyzer.analyze(stock.code, factor_data=factor_data)

        # Verify score_factors was called with our factor_data
        mock_service.score_factors.assert_called_once_with(
            stock.code, stock.name, factor_data
        )
        assert result.score == 65.0


# ---------------------------------------------------------------------------
# 8. test_ai_analyzer_gathers_data_when_no_kwargs
# ---------------------------------------------------------------------------


class TestAIAnalyzerGathersData:
    @patch("apps.quant.ai.service.AIService")
    @patch.object(AIAnalyzer, "_gather_factor_data")
    def test_ai_analyzer_gathers_data_when_no_kwargs(
        self, mock_gather, MockAIService, stock
    ):
        """Without factor_data kwarg, _gather_factor_data should be called."""
        mock_gather.return_value = {"stock_code": stock.code}
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 55,
            "reasoning": "Auto-gathered data",
            "risk_factors": [],
            "catalysts": [],
        }

        analyzer = AIAnalyzer()
        analyzer.analyze(stock.code)

        mock_gather.assert_called_once_with(stock.code)


# ---------------------------------------------------------------------------
# 9. test_ai_analyzer_details_include_provider
# ---------------------------------------------------------------------------


class TestAIAnalyzerDetailsIncludeProvider:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_details_include_provider(self, MockAIService, stock):
        """Result details dict should include the provider name."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 60,
            "reasoning": "Test",
            "risk_factors": [],
            "catalysts": [],
        }

        analyzer = AIAnalyzer(provider="deepseek")
        result = analyzer.analyze(stock.code)

        assert result.details["provider"] == "deepseek"

    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_details_include_chatgpt_provider(self, MockAIService, stock):
        """Result details should reflect chatgpt when used."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 60,
            "reasoning": "Test",
            "risk_factors": [],
            "catalysts": [],
        }

        analyzer = AIAnalyzer(provider="chatgpt")
        result = analyzer.analyze(stock.code)

        assert result.details["provider"] == "chatgpt"


# ---------------------------------------------------------------------------
# 10. test_ai_analyzer_confidence_with_reasoning
# ---------------------------------------------------------------------------


class TestAIAnalyzerConfidenceWithReasoning:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_confidence_with_reasoning(self, MockAIService, stock):
        """With reasoning present, confidence should be 0.7."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 60,
            "reasoning": "Strong fundamentals with growth potential",
            "risk_factors": [],
            "catalysts": [],
        }

        analyzer = AIAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.confidence == 0.7


# ---------------------------------------------------------------------------
# 11. test_ai_analyzer_confidence_without_reasoning
# ---------------------------------------------------------------------------


class TestAIAnalyzerConfidenceWithoutReasoning:
    @patch("apps.quant.ai.service.AIService")
    def test_ai_analyzer_confidence_without_reasoning(self, MockAIService, stock):
        """Without reasoning (empty string), confidence should be 0.3."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.return_value = {
            "adjusted_score": 60,
            "reasoning": "",
            "risk_factors": [],
            "catalysts": [],
        }

        analyzer = AIAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.confidence == 0.3


# ---------------------------------------------------------------------------
# 12. test_generate_report_success
# ---------------------------------------------------------------------------


class TestGenerateReportSuccess:
    @patch("apps.quant.ai.service.AIService")
    def test_generate_report_success(self, MockAIService, stock):
        """generate_report should return dict from AI service."""
        expected_report = {
            "summary": "Overall positive",
            "technical": "Upward trend",
            "fundamental": "Strong financials",
            "risks": ["Market risk"],
            "recommendation": "Buy",
        }
        mock_service = MockAIService.return_value
        mock_service.generate_report.return_value = expected_report

        analyzer = AIAnalyzer()
        result = analyzer.generate_report(stock.code, {"score": 75})

        assert result == expected_report
        mock_service.generate_report.assert_called_once_with(
            stock.code, stock.name, {"score": 75}
        )


# ---------------------------------------------------------------------------
# 13. test_generate_report_service_error
# ---------------------------------------------------------------------------


class TestGenerateReportServiceError:
    @patch("apps.quant.ai.service.AIService")
    def test_generate_report_service_error(self, MockAIService, stock):
        """generate_report should return error dict on AIServiceError."""
        from apps.quant.ai.service import AIServiceError

        mock_service = MockAIService.return_value
        mock_service.generate_report.side_effect = AIServiceError("API down")

        analyzer = AIAnalyzer()
        result = analyzer.generate_report(stock.code, {"score": 75})

        assert "error" in result
        assert result["error"] == "API down"

    @pytest.mark.django_db
    def test_generate_report_stock_not_found(self):
        """generate_report returns error dict for non-existent stock."""
        analyzer = AIAnalyzer()
        result = analyzer.generate_report("NONEXISTENT_999", {"score": 75})

        assert result == {"error": "Stock not found"}


# ---------------------------------------------------------------------------
# 14. test_gather_factor_data
# ---------------------------------------------------------------------------


class TestGatherFactorData:
    @pytest.mark.django_db
    def test_gather_factor_data(self, stock):
        """_gather_factor_data should collect financial and kline data."""
        # Create financial report
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            pe_ratio=Decimal("10.5"),
            pb_ratio=Decimal("1.2"),
            roe=Decimal("15.0"),
            revenue=Decimal("100000.0"),
            net_profit=Decimal("20000.0"),
        )

        # Create kline data
        for i in range(3):
            KlineData.objects.create(
                stock=stock,
                date=datetime.date(2025, 1, 10 + i),
                open=Decimal("10.00"),
                high=Decimal("11.00"),
                low=Decimal("9.00"),
                close=Decimal(str(10.0 + i * 0.5)),
                volume=100000 + i * 1000,
                amount=Decimal("1000000.00"),
                change_pct=Decimal(str(1.5 + i * 0.1)),
            )

        data = AIAnalyzer._gather_factor_data(stock.code)

        assert data["stock_code"] == stock.code
        assert "financial" in data
        assert data["financial"]["period"] == "2025Q3"
        assert data["financial"]["pe_ratio"] == 10.5
        assert data["financial"]["pb_ratio"] == 1.2
        assert data["financial"]["roe"] == 15.0
        assert data["financial"]["revenue"] == 100000.0
        assert data["financial"]["net_profit"] == 20000.0

        assert "recent_prices" in data
        assert len(data["recent_prices"]) == 3
        # Should be ordered by date descending (most recent first)
        assert data["recent_prices"][0]["close"] == 11.0  # Jan 12
        assert data["recent_prices"][0]["volume"] == 102000

    @pytest.mark.django_db
    def test_gather_factor_data_empty(self, stock):
        """_gather_factor_data returns minimal dict when no data exists."""
        data = AIAnalyzer._gather_factor_data(stock.code)

        assert data["stock_code"] == stock.code
        assert "financial" not in data
        assert "recent_prices" not in data


# ---------------------------------------------------------------------------
# 15. test_safe_analyze_fallback
# ---------------------------------------------------------------------------


class TestSafeAnalyzeFallback:
    @patch("apps.quant.ai.service.AIService")
    def test_safe_analyze_fallback(self, MockAIService, stock):
        """safe_analyze() should catch unexpected exceptions and return neutral HOLD."""
        mock_service = MockAIService.return_value
        mock_service.score_factors.side_effect = RuntimeError("Unexpected crash")

        analyzer = AIAnalyzer()
        result = analyzer.safe_analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.score == 50.0
        assert result.confidence == 0.0
        assert "failed" in result.explanation.lower()
