"""Tests for MoneyFlowAnalyzer (main net trend, big orders, retail divergence, momentum)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest

from apps.quant.analyzers.money_flow import MoneyFlowAnalyzer
from apps.quant.analyzers.types import AnalysisResult, Signal
from apps.quant.models import MoneyFlow, StockBasic

# ---------------------------------------------------------------------------
# Fixtures / helpers
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


def create_bullish_flows(stock, days=15):
    """Create money-flow data with strong main-force inflow and institutional buying."""
    flows = []
    for i in range(days):
        d = datetime.date(2025, 1, 1) + timedelta(days=i)
        # Main force heavily buying; retail selling (divergence = bullish).
        flows.append(
            MoneyFlow(
                stock=stock,
                date=d,
                main_net=Decimal(str(5_000_000 + i * 200_000)),
                huge_net=Decimal(str(3_000_000 + i * 100_000)),
                big_net=Decimal(str(2_000_000 + i * 100_000)),
                mid_net=Decimal(str(-1_000_000)),
                small_net=Decimal(str(-1_500_000)),
            )
        )
    MoneyFlow.objects.bulk_create(flows)
    return flows


def create_bearish_flows(stock, days=15):
    """Create money-flow data with strong main-force outflow."""
    flows = []
    for i in range(days):
        d = datetime.date(2025, 1, 1) + timedelta(days=i)
        # Main force heavily selling; retail buying (bearish divergence).
        flows.append(
            MoneyFlow(
                stock=stock,
                date=d,
                main_net=Decimal(str(-5_000_000 - i * 200_000)),
                huge_net=Decimal(str(-3_000_000 - i * 100_000)),
                big_net=Decimal(str(-2_000_000 - i * 100_000)),
                mid_net=Decimal(str(1_000_000)),
                small_net=Decimal(str(1_500_000)),
            )
        )
    MoneyFlow.objects.bulk_create(flows)
    return flows


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMoneyFlowAnalyzerName:
    def test_name(self):
        """Verify the analyzer name is 'money_flow'."""
        analyzer = MoneyFlowAnalyzer()
        assert analyzer.name == "money_flow"


@pytest.mark.django_db
class TestMoneyFlowBullish:
    def test_bullish_score(self, stock):
        """Strong main-force inflow should yield a bullish score above 55."""
        create_bullish_flows(stock, days=15)
        analyzer = MoneyFlowAnalyzer(lookback_days=20)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score > 55, (
            f"Expected bullish score > 55, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.SELL


@pytest.mark.django_db
class TestMoneyFlowBearish:
    def test_bearish_score(self, stock):
        """Strong main-force outflow should yield a bearish score below 45."""
        create_bearish_flows(stock, days=15)
        analyzer = MoneyFlowAnalyzer(lookback_days=20)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score < 45, (
            f"Expected bearish score < 45, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.BUY


@pytest.mark.django_db
class TestMoneyFlowInsufficientData:
    def test_insufficient_data(self, stock):
        """Only 3 days of data should return HOLD with confidence 0."""
        for i in range(3):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            MoneyFlow.objects.create(
                stock=stock,
                date=d,
                main_net=Decimal("100000"),
                huge_net=Decimal("50000"),
                big_net=Decimal("50000"),
                mid_net=Decimal("-20000"),
                small_net=Decimal("-30000"),
            )

        analyzer = MoneyFlowAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert result.score == 50.0


@pytest.mark.django_db
class TestMoneyFlowComponentScores:
    def test_component_scores_in_details(self, stock):
        """Details should contain component_scores dict with all 4 keys."""
        create_bullish_flows(stock, days=10)
        analyzer = MoneyFlowAnalyzer()
        result = analyzer.analyze(stock.code)

        assert "component_scores" in result.details
        scores = result.details["component_scores"]
        expected_keys = {"main_net_trend", "big_order_ratio", "retail_flow", "flow_momentum"}
        assert set(scores.keys()) == expected_keys

        for key, val in scores.items():
            assert 0.0 <= val <= 100.0, f"{key} score {val} out of range"


@pytest.mark.django_db
class TestMoneyFlowConfidence:
    def test_confidence_high_data(self, stock):
        """15 days of data should yield confidence >= 0.5."""
        create_bullish_flows(stock, days=15)
        analyzer = MoneyFlowAnalyzer(lookback_days=20)
        result = analyzer.analyze(stock.code)

        assert result.confidence >= 0.5

    def test_confidence_moderate_data(self, stock):
        """5 days of data should yield confidence 0.5."""
        for i in range(5):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            MoneyFlow.objects.create(
                stock=stock,
                date=d,
                main_net=Decimal("100000"),
                huge_net=Decimal("50000"),
                big_net=Decimal("50000"),
                mid_net=Decimal("-20000"),
                small_net=Decimal("-30000"),
            )

        analyzer = MoneyFlowAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.confidence == 0.5


@pytest.mark.django_db
class TestMoneyFlowSafeAnalyze:
    def test_safe_analyze_missing_stock(self):
        """safe_analyze for a non-existent stock code returns HOLD."""
        analyzer = MoneyFlowAnalyzer()
        result = analyzer.safe_analyze("DOESNOTEXIST")

        assert isinstance(result, AnalysisResult)
        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0


@pytest.mark.django_db
class TestMoneyFlowRetailDivergence:
    def test_bullish_divergence_component(self, stock):
        """Main buying + retail selling = bullish retail_flow score."""
        for i in range(10):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            MoneyFlow.objects.create(
                stock=stock,
                date=d,
                main_net=Decimal("5000000"),
                huge_net=Decimal("3000000"),
                big_net=Decimal("2000000"),
                mid_net=Decimal("-2000000"),
                small_net=Decimal("-3000000"),
            )

        analyzer = MoneyFlowAnalyzer()
        result = analyzer.analyze(stock.code)
        retail_score = result.details["component_scores"]["retail_flow"]
        assert retail_score > 60, f"Expected bullish retail divergence, got {retail_score}"
