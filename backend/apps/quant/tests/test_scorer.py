"""Tests for MultiFactorScorer."""

import math
from unittest.mock import patch, MagicMock

import pytest

from apps.quant.analyzers.scorer import MultiFactorScorer
from apps.quant.analyzers.types import AnalysisResult, Signal, TradingStyle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(score=50.0, signal=Signal.HOLD, confidence=0.5, explanation="test"):
    """Create an AnalysisResult with convenient defaults."""
    return AnalysisResult(
        score=score,
        signal=signal,
        confidence=confidence,
        explanation=explanation,
        details={},
    )


# ---------------------------------------------------------------------------
# Test: Default style
# ---------------------------------------------------------------------------


class TestScorerDefaultStyle:
    def test_scorer_default_style(self):
        """Default style should be SWING."""
        scorer = MultiFactorScorer()
        assert scorer.style == TradingStyle.SWING


# ---------------------------------------------------------------------------
# Test: Weights sum to 1.0 for every style
# ---------------------------------------------------------------------------


class TestScorerWeightsSumToOne:
    @pytest.mark.parametrize("style", list(TradingStyle))
    def test_scorer_weights_sum_to_one(self, style):
        """Weights for each trading style must sum to 1.0."""
        weights = MultiFactorScorer.STYLE_WEIGHTS[style]
        assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Test: ULTRA_SHORT weights / analyzers
# ---------------------------------------------------------------------------


class TestScorerUltraShortWeights:
    def test_scorer_ultra_short_weights(self):
        """ULTRA_SHORT should use technical, money_flow, chip, sentiment,
        game_theory, behavior_finance."""
        weights = MultiFactorScorer.STYLE_WEIGHTS[TradingStyle.ULTRA_SHORT]
        expected_keys = {
            "technical",
            "money_flow",
            "chip",
            "sentiment",
            "game_theory",
            "behavior_finance",
        }
        assert set(weights.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Test: MID_LONG weights / analyzers
# ---------------------------------------------------------------------------


class TestScorerMidLongWeights:
    def test_scorer_mid_long_weights(self):
        """MID_LONG should use all 10 analyzers (including ai)."""
        weights = MultiFactorScorer.STYLE_WEIGHTS[TradingStyle.MID_LONG]
        expected_keys = {
            "technical",
            "fundamental",
            "money_flow",
            "chip",
            "sentiment",
            "sector_rotation",
            "macro",
            "behavior_finance",
            "game_theory",
            "ai",
        }
        assert set(weights.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Test: Only builds needed analyzers
# ---------------------------------------------------------------------------


class TestScorerOnlyBuildsNeededAnalyzers:
    def test_scorer_only_builds_needed_analyzers(self):
        """ULTRA_SHORT should NOT include fundamental, sector_rotation, or macro."""
        scorer = MultiFactorScorer(style=TradingStyle.ULTRA_SHORT)
        assert "fundamental" not in scorer._analyzers
        assert "sector_rotation" not in scorer._analyzers
        assert "macro" not in scorer._analyzers
        # But should include these:
        assert "technical" in scorer._analyzers
        assert "money_flow" in scorer._analyzers
        assert "chip" in scorer._analyzers
        assert "sentiment" in scorer._analyzers
        assert "game_theory" in scorer._analyzers
        assert "behavior_finance" in scorer._analyzers


# ---------------------------------------------------------------------------
# Test: score() returns all required keys
# ---------------------------------------------------------------------------


class TestScoreReturnsRequiredKeys:
    def test_score_returns_required_keys(self):
        """score() must return dict with all required keys."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        # Mock all analyzers to avoid DB hits
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(return_value=_make_result())

        result = scorer.score("000001")
        required_keys = {
            "final_score",
            "signal",
            "confidence",
            "style",
            "explanation",
            "analyzer_results",
            "component_scores",
        }
        assert required_keys == set(result.keys())


# ---------------------------------------------------------------------------
# Test: final_score range
# ---------------------------------------------------------------------------


class TestScoreFinalScoreRange:
    def test_score_final_score_range(self):
        """final_score must be between 0 and 100."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(return_value=_make_result())

        result = scorer.score("000001")
        assert 0 <= result["final_score"] <= 100


# ---------------------------------------------------------------------------
# Test: confidence range
# ---------------------------------------------------------------------------


class TestScoreConfidenceRange:
    def test_score_confidence_range(self):
        """confidence must be between 0 and 1."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(return_value=_make_result())

        result = scorer.score("000001")
        assert 0 <= result["confidence"] <= 1


# ---------------------------------------------------------------------------
# Test: signal matches score thresholds
# ---------------------------------------------------------------------------


class TestScoreSignalMatchesThreshold:
    def test_buy_signal_when_score_high(self):
        """Signal should be BUY when final_score >= 70."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(
                return_value=_make_result(score=85.0, signal=Signal.BUY, confidence=0.8)
            )

        result = scorer.score("000001")
        assert result["final_score"] >= 70
        assert result["signal"] == Signal.BUY

    def test_sell_signal_when_score_low(self):
        """Signal should be SELL when final_score <= 30."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(
                return_value=_make_result(score=15.0, signal=Signal.SELL, confidence=0.8)
            )

        result = scorer.score("000001")
        assert result["final_score"] <= 30
        assert result["signal"] == Signal.SELL

    def test_hold_signal_when_score_mid(self):
        """Signal should be HOLD when 30 < final_score < 70."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(
                return_value=_make_result(score=50.0, signal=Signal.HOLD, confidence=0.8)
            )

        result = scorer.score("000001")
        assert 30 < result["final_score"] < 70
        assert result["signal"] == Signal.HOLD


# ---------------------------------------------------------------------------
# Test: Mocked analyzers verify weighted calculation
# ---------------------------------------------------------------------------


class TestScoreWithMockedAnalyzers:
    def test_score_with_mocked_analyzers(self):
        """Mock all analyzers to known values and verify weighted calculation."""
        scorer = MultiFactorScorer(style=TradingStyle.ULTRA_SHORT)
        weights = MultiFactorScorer.STYLE_WEIGHTS[TradingStyle.ULTRA_SHORT]

        # Set up known results per analyzer
        mock_results = {
            "technical": _make_result(score=80.0, confidence=1.0),
            "money_flow": _make_result(score=60.0, confidence=1.0),
            "chip": _make_result(score=40.0, confidence=1.0),
            "sentiment": _make_result(score=70.0, confidence=1.0),
            "game_theory": _make_result(score=50.0, confidence=1.0),
            "behavior_finance": _make_result(score=55.0, confidence=1.0),
        }

        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(return_value=mock_results[name])

        result = scorer.score("000001")

        # With confidence=1.0 for all, effective_weight == w, so:
        # weighted_sum = sum(score * w) / sum(w) = sum(score * w) / 1.0
        expected = sum(
            mock_results[name].score * weights[name] for name in mock_results
        )
        assert math.isclose(result["final_score"], round(expected, 2), rel_tol=1e-9)

        # Check component_scores
        for name in mock_results:
            expected_comp = round(mock_results[name].score * weights[name], 2)
            assert result["component_scores"][name] == expected_comp


# ---------------------------------------------------------------------------
# Test: Confidence weighting
# ---------------------------------------------------------------------------


class TestScoreConfidenceWeighting:
    def test_score_confidence_weighting(self):
        """Low confidence analyzer should have less influence on final score."""
        scorer_high = MultiFactorScorer(style=TradingStyle.ULTRA_SHORT)
        scorer_low = MultiFactorScorer(style=TradingStyle.ULTRA_SHORT)

        # All analyzers return 80, except technical:
        # In scorer_high: technical has confidence=1.0
        # In scorer_low:  technical has confidence=0.1 (near min of 0.1)
        base = _make_result(score=50.0, confidence=1.0)

        for name, analyzer in scorer_high._analyzers.items():
            if name == "technical":
                analyzer.safe_analyze = MagicMock(
                    return_value=_make_result(score=90.0, confidence=1.0)
                )
            else:
                analyzer.safe_analyze = MagicMock(return_value=base)

        for name, analyzer in scorer_low._analyzers.items():
            if name == "technical":
                # Same high score, but very low confidence
                analyzer.safe_analyze = MagicMock(
                    return_value=_make_result(score=90.0, confidence=0.1)
                )
            else:
                analyzer.safe_analyze = MagicMock(return_value=base)

        result_high = scorer_high.score("000001")
        result_low = scorer_low.score("000001")

        # When technical has high confidence, it pulls the score up more
        assert result_high["final_score"] > result_low["final_score"]


# ---------------------------------------------------------------------------
# Test: Explanation format
# ---------------------------------------------------------------------------


class TestExplanationFormat:
    def test_explanation_format(self):
        """Explanation must include the style name."""
        scorer = MultiFactorScorer(style=TradingStyle.ULTRA_SHORT)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(return_value=_make_result())

        result = scorer.score("000001")
        assert TradingStyle.ULTRA_SHORT.value in result["explanation"]

    def test_explanation_includes_bullish_prefix(self):
        """Explanation should include 'bullish' for BUY signal."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(
                return_value=_make_result(score=85.0, confidence=0.9)
            )

        result = scorer.score("000001")
        assert "bullish" in result["explanation"].lower()

    def test_explanation_includes_bearish_prefix(self):
        """Explanation should include 'bearish' for SELL signal."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        for name, analyzer in scorer._analyzers.items():
            analyzer.safe_analyze = MagicMock(
                return_value=_make_result(score=15.0, confidence=0.9)
            )

        result = scorer.score("000001")
        assert "bearish" in result["explanation"].lower()


# ---------------------------------------------------------------------------
# Test: Handles missing stock (DB test)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestScoreHandlesMissingStock:
    def test_score_handles_missing_stock(self):
        """Non-existent stock should return a neutral result via safe_analyze fallbacks."""
        scorer = MultiFactorScorer(style=TradingStyle.SWING)
        result = scorer.score("NONEXISTENT_999999")

        # All analyzers should fall back to safe_analyze neutral (score=50, confidence=0)
        assert 0 <= result["final_score"] <= 100
        assert 0 <= result["confidence"] <= 1
        assert isinstance(result["signal"], Signal)
        # With all failures, confidence should be very low
        assert result["confidence"] <= 0.1
