import pytest

from apps.quant.analyzers.types import AnalysisResult, Signal, TradingStyle
from apps.quant.analyzers.base import AnalyzerBase


class TestAnalysisResult:
    def test_analysis_result_creation(self):
        """Create a valid AnalysisResult and verify all fields."""
        result = AnalysisResult(
            score=75.0,
            signal=Signal.BUY,
            confidence=0.85,
            explanation="Strong upward momentum",
            details={"rsi": 65.3},
        )
        assert result.score == 75.0
        assert result.signal == Signal.BUY
        assert result.confidence == 0.85
        assert result.explanation == "Strong upward momentum"
        assert result.details == {"rsi": 65.3}

    def test_analysis_result_score_validation(self):
        """Score < 0 or > 100 raises ValueError."""
        with pytest.raises(ValueError, match="Score must be 0-100"):
            AnalysisResult(
                score=-1.0,
                signal=Signal.HOLD,
                confidence=0.5,
                explanation="test",
            )
        with pytest.raises(ValueError, match="Score must be 0-100"):
            AnalysisResult(
                score=101.0,
                signal=Signal.HOLD,
                confidence=0.5,
                explanation="test",
            )

    def test_analysis_result_confidence_validation(self):
        """Confidence < 0 or > 1 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=-0.1,
                explanation="test",
            )
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=1.1,
                explanation="test",
            )

    def test_analysis_result_default_details(self):
        """Details defaults to empty dict."""
        result = AnalysisResult(
            score=50.0,
            signal=Signal.HOLD,
            confidence=0.5,
            explanation="test",
        )
        assert result.details == {}


class TestSignalEnum:
    def test_signal_enum_values(self):
        """BUY, SELL, HOLD values exist and are correct."""
        assert Signal.BUY.value == "BUY"
        assert Signal.SELL.value == "SELL"
        assert Signal.HOLD.value == "HOLD"
        assert len(Signal) == 3


class TestTradingStyleEnum:
    def test_trading_style_enum_values(self):
        """Three trading styles exist with correct values."""
        assert TradingStyle.ULTRA_SHORT.value == "ultra_short"
        assert TradingStyle.SWING.value == "swing"
        assert TradingStyle.MID_LONG.value == "mid_long"
        assert len(TradingStyle) == 3


class TestAnalyzerBase:
    def test_analyzer_base_is_abstract(self):
        """Cannot instantiate AnalyzerBase directly."""
        with pytest.raises(TypeError):
            AnalyzerBase()

    def test_concrete_analyzer(self):
        """Create a minimal concrete analyzer, call analyze, verify returns AnalysisResult."""

        class DummyAnalyzer(AnalyzerBase):
            name = "dummy"
            description = "A dummy analyzer for testing"

            def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
                return AnalysisResult(
                    score=80.0,
                    signal=Signal.BUY,
                    confidence=0.9,
                    explanation=f"Dummy analysis for {stock_code}",
                )

        analyzer = DummyAnalyzer()
        result = analyzer.analyze("000001")
        assert isinstance(result, AnalysisResult)
        assert result.score == 80.0
        assert result.signal == Signal.BUY
        assert result.confidence == 0.9
        assert "000001" in result.explanation

    def test_safe_analyze_catches_exceptions(self):
        """Concrete analyzer that raises; safe_analyze returns neutral result with confidence=0."""

        class FailingAnalyzer(AnalyzerBase):
            name = "failing"

            def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
                raise RuntimeError("Something went wrong")

        analyzer = FailingAnalyzer()
        result = analyzer.safe_analyze("000001")
        assert isinstance(result, AnalysisResult)
        assert result.score == 50.0
        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert "Analysis failed" in result.explanation
        assert result.details["error"] == "Something went wrong"

    def test_safe_analyze_passes_through_success(self):
        """Working analyzer; safe_analyze returns normal result."""

        class GoodAnalyzer(AnalyzerBase):
            name = "good"

            def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
                return AnalysisResult(
                    score=90.0,
                    signal=Signal.BUY,
                    confidence=0.95,
                    explanation="All good",
                )

        analyzer = GoodAnalyzer()
        result = analyzer.safe_analyze("000001")
        assert result.score == 90.0
        assert result.signal == Signal.BUY
        assert result.confidence == 0.95
        assert result.explanation == "All good"
