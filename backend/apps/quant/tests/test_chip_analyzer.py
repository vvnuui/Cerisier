"""Tests for ChipAnalyzer (margin trend, short pressure, leverage ratio, momentum)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest

from apps.quant.analyzers.chip import ChipAnalyzer
from apps.quant.analyzers.types import AnalysisResult, Signal
from apps.quant.models import MarginData, StockBasic

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def stock(db):
    return StockBasic.objects.create(
        code="600519",
        name="贵州茅台",
        industry="白酒",
        sector="消费",
        market="SH",
        list_date=datetime.date(2001, 8, 27),
        is_active=True,
    )


def create_bullish_margin(stock, days=15):
    """Create margin data with increasing margin balance and decreasing shorts."""
    records = []
    base_margin = 100_000_000
    base_short = 50_000_000
    for i in range(days):
        d = datetime.date(2025, 1, 1) + timedelta(days=i)
        records.append(
            MarginData(
                stock=stock,
                date=d,
                margin_balance=Decimal(str(base_margin + i * 2_000_000)),
                short_balance=Decimal(str(base_short - i * 1_000_000)),
                margin_buy=Decimal(str(8_000_000)),
                margin_repay=Decimal(str(5_000_000)),
            )
        )
    MarginData.objects.bulk_create(records)
    return records


def create_bearish_margin(stock, days=15):
    """Create margin data with decreasing margin balance and increasing shorts."""
    records = []
    base_margin = 100_000_000
    base_short = 20_000_000
    for i in range(days):
        d = datetime.date(2025, 1, 1) + timedelta(days=i)
        records.append(
            MarginData(
                stock=stock,
                date=d,
                margin_balance=Decimal(str(base_margin - i * 2_000_000)),
                short_balance=Decimal(str(base_short + i * 1_500_000)),
                margin_buy=Decimal(str(3_000_000)),
                margin_repay=Decimal(str(7_000_000)),
            )
        )
    MarginData.objects.bulk_create(records)
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChipAnalyzerName:
    def test_name(self):
        """Verify the analyzer name is 'chip'."""
        analyzer = ChipAnalyzer()
        assert analyzer.name == "chip"


@pytest.mark.django_db
class TestChipBullish:
    def test_bullish_score(self, stock):
        """Increasing margin + decreasing shorts should yield bullish score > 55."""
        create_bullish_margin(stock, days=15)
        analyzer = ChipAnalyzer(lookback_days=20)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score > 55, (
            f"Expected bullish score > 55, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.SELL


@pytest.mark.django_db
class TestChipBearish:
    def test_bearish_score(self, stock):
        """Decreasing margin + increasing shorts should yield bearish score < 45."""
        create_bearish_margin(stock, days=15)
        analyzer = ChipAnalyzer(lookback_days=20)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score < 45, (
            f"Expected bearish score < 45, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.BUY


@pytest.mark.django_db
class TestChipInsufficientData:
    def test_insufficient_data(self, stock):
        """Only 3 days of data should return HOLD with confidence 0."""
        for i in range(3):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            MarginData.objects.create(
                stock=stock,
                date=d,
                margin_balance=Decimal("100000000"),
                short_balance=Decimal("50000000"),
                margin_buy=Decimal("5000000"),
                margin_repay=Decimal("5000000"),
            )

        analyzer = ChipAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert result.score == 50.0


@pytest.mark.django_db
class TestChipComponentScores:
    def test_component_scores_in_details(self, stock):
        """Details should contain component_scores dict with all 4 keys."""
        create_bullish_margin(stock, days=10)
        analyzer = ChipAnalyzer()
        result = analyzer.analyze(stock.code)

        assert "component_scores" in result.details
        scores = result.details["component_scores"]
        expected_keys = {"margin_trend", "short_pressure", "leverage_ratio", "balance_momentum"}
        assert set(scores.keys()) == expected_keys

        for key, val in scores.items():
            assert 0.0 <= val <= 100.0, f"{key} score {val} out of range"


@pytest.mark.django_db
class TestChipConfidence:
    def test_confidence_high_data(self, stock):
        """15 days of data should yield confidence >= 0.5."""
        create_bullish_margin(stock, days=15)
        analyzer = ChipAnalyzer(lookback_days=20)
        result = analyzer.analyze(stock.code)

        assert result.confidence >= 0.5

    def test_confidence_moderate_data(self, stock):
        """5 days of data should yield confidence 0.5."""
        for i in range(5):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            MarginData.objects.create(
                stock=stock,
                date=d,
                margin_balance=Decimal("100000000"),
                short_balance=Decimal("50000000"),
                margin_buy=Decimal("5000000"),
                margin_repay=Decimal("5000000"),
            )

        analyzer = ChipAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.confidence == 0.5


@pytest.mark.django_db
class TestChipSafeAnalyze:
    def test_safe_analyze_missing_stock(self):
        """safe_analyze for a non-existent stock code returns HOLD."""
        analyzer = ChipAnalyzer()
        result = analyzer.safe_analyze("DOESNOTEXIST")

        assert isinstance(result, AnalysisResult)
        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0


@pytest.mark.django_db
class TestChipLeverageComponent:
    def test_leverage_buy_dominant(self, stock):
        """When margin_buy >> margin_repay, leverage score should be bullish."""
        for i in range(10):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            MarginData.objects.create(
                stock=stock,
                date=d,
                margin_balance=Decimal("100000000"),
                short_balance=Decimal("50000000"),
                margin_buy=Decimal("10000000"),
                margin_repay=Decimal("5000000"),
            )

        analyzer = ChipAnalyzer()
        result = analyzer.analyze(stock.code)
        leverage_score = result.details["component_scores"]["leverage_ratio"]
        assert leverage_score > 60, f"Expected bullish leverage, got {leverage_score}"

    def test_leverage_repay_dominant(self, stock):
        """When margin_repay >> margin_buy, leverage score should be bearish."""
        for i in range(10):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            MarginData.objects.create(
                stock=stock,
                date=d,
                margin_balance=Decimal("100000000"),
                short_balance=Decimal("50000000"),
                margin_buy=Decimal("3000000"),
                margin_repay=Decimal("8000000"),
            )

        analyzer = ChipAnalyzer()
        result = analyzer.analyze(stock.code)
        leverage_score = result.details["component_scores"]["leverage_ratio"]
        assert leverage_score < 40, f"Expected bearish leverage, got {leverage_score}"
