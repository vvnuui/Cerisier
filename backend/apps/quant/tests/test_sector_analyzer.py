"""Tests for SectorRotationAnalyzer (sector momentum, flow, relative strength)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest

from apps.quant.analyzers.sector import SectorRotationAnalyzer
from apps.quant.analyzers.types import AnalysisResult, Signal
from apps.quant.models import KlineData, MoneyFlow, StockBasic

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def sector_stocks(db):
    """Create 4 stocks in the same industry."""
    stocks = []
    for i, (code, name) in enumerate([
        ("600036", "招商银行"),
        ("601398", "工商银行"),
        ("601288", "农业银行"),
        ("000001", "平安银行"),
    ]):
        stocks.append(
            StockBasic.objects.create(
                code=code,
                name=name,
                industry="银行",
                sector="金融",
                market="SH" if code.startswith("6") else "SZ",
                list_date=datetime.date(2000, 1, 1),
                is_active=True,
            )
        )
    return stocks


def create_sector_klines_bullish(stocks, days=15):
    """Create uptrend kline data for all stocks in the sector."""
    for stock in stocks:
        base_price = 10.0
        klines = []
        for i in range(days):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            price = base_price * (1 + 0.01 * i)  # 1% daily increase.
            klines.append(
                KlineData(
                    stock=stock,
                    date=d,
                    open=Decimal(str(round(price * 0.99, 4))),
                    high=Decimal(str(round(price * 1.01, 4))),
                    low=Decimal(str(round(price * 0.98, 4))),
                    close=Decimal(str(round(price, 4))),
                    volume=100000,
                    amount=Decimal(str(round(price * 100000, 4))),
                )
            )
        KlineData.objects.bulk_create(klines)


def create_sector_klines_bearish(stocks, days=15):
    """Create downtrend kline data for all stocks in the sector."""
    for stock in stocks:
        base_price = 20.0
        klines = []
        for i in range(days):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            price = base_price * (1 - 0.01 * i)  # 1% daily decrease.
            klines.append(
                KlineData(
                    stock=stock,
                    date=d,
                    open=Decimal(str(round(price * 1.01, 4))),
                    high=Decimal(str(round(price * 1.02, 4))),
                    low=Decimal(str(round(price * 0.99, 4))),
                    close=Decimal(str(round(price, 4))),
                    volume=100000,
                    amount=Decimal(str(round(price * 100000, 4))),
                )
            )
        KlineData.objects.bulk_create(klines)


def create_sector_money_flows_bullish(stocks, days=15):
    """Create positive money flow data for all stocks in the sector."""
    for stock in stocks:
        flows = []
        for i in range(days):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            flows.append(
                MoneyFlow(
                    stock=stock,
                    date=d,
                    main_net=Decimal(str(3_000_000)),
                    huge_net=Decimal(str(1_500_000)),
                    big_net=Decimal(str(1_500_000)),
                    mid_net=Decimal(str(-500_000)),
                    small_net=Decimal(str(-500_000)),
                )
            )
        MoneyFlow.objects.bulk_create(flows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSectorAnalyzerName:
    def test_name(self):
        """Verify the analyzer name is 'sector_rotation'."""
        analyzer = SectorRotationAnalyzer()
        assert analyzer.name == "sector_rotation"


@pytest.mark.django_db
class TestSectorBullish:
    def test_bullish_score(self, sector_stocks):
        """Sector uptrend with positive flow should yield bullish score > 55."""
        create_sector_klines_bullish(sector_stocks, days=15)
        create_sector_money_flows_bullish(sector_stocks, days=15)

        analyzer = SectorRotationAnalyzer(lookback_days=20)
        result = analyzer.analyze(sector_stocks[0].code)

        assert isinstance(result, AnalysisResult)
        assert result.score > 55, (
            f"Expected bullish score > 55, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.SELL


@pytest.mark.django_db
class TestSectorBearish:
    def test_bearish_score(self, sector_stocks):
        """Sector downtrend should yield bearish score < 45."""
        create_sector_klines_bearish(sector_stocks, days=15)

        analyzer = SectorRotationAnalyzer(lookback_days=20)
        result = analyzer.analyze(sector_stocks[0].code)

        assert isinstance(result, AnalysisResult)
        assert result.score < 45, (
            f"Expected bearish score < 45, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.BUY


@pytest.mark.django_db
class TestSectorInsufficientData:
    def test_no_kline_data(self, sector_stocks):
        """No kline data should return HOLD with confidence 0."""
        analyzer = SectorRotationAnalyzer()
        result = analyzer.analyze(sector_stocks[0].code)

        assert result.signal == Signal.HOLD
        assert result.score == 50.0

    def test_stock_not_found(self, db):
        """Non-existent stock should return HOLD."""
        analyzer = SectorRotationAnalyzer()
        result = analyzer.analyze("DOESNOTEXIST")

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0

    def test_no_industry(self, db):
        """Stock with no industry should return HOLD."""
        StockBasic.objects.create(
            code="999999",
            name="测试股票",
            industry="",
            sector="",
            market="SZ",
            is_active=True,
        )
        analyzer = SectorRotationAnalyzer()
        result = analyzer.analyze("999999")

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0

    def test_few_sector_stocks(self, db):
        """Only 2 stocks in sector (< 3) should return HOLD."""
        StockBasic.objects.create(
            code="600036",
            name="招商银行",
            industry="稀有行业",
            sector="金融",
            market="SH",
            is_active=True,
        )
        StockBasic.objects.create(
            code="601398",
            name="工商银行",
            industry="稀有行业",
            sector="金融",
            market="SH",
            is_active=True,
        )
        analyzer = SectorRotationAnalyzer()
        result = analyzer.analyze("600036")

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0


@pytest.mark.django_db
class TestSectorComponentScores:
    def test_component_scores_in_details(self, sector_stocks):
        """Details should contain component_scores dict with all 3 keys."""
        create_sector_klines_bullish(sector_stocks, days=15)
        analyzer = SectorRotationAnalyzer()
        result = analyzer.analyze(sector_stocks[0].code)

        assert "component_scores" in result.details
        scores = result.details["component_scores"]
        expected_keys = {"sector_momentum", "sector_flow", "relative_strength"}
        assert set(scores.keys()) == expected_keys

        for key, val in scores.items():
            assert 0.0 <= val <= 100.0, f"{key} score {val} out of range"


@pytest.mark.django_db
class TestSectorConfidence:
    def test_confidence_full_coverage(self, sector_stocks):
        """All 4 stocks with data should yield high confidence."""
        create_sector_klines_bullish(sector_stocks, days=15)
        analyzer = SectorRotationAnalyzer(lookback_days=20)
        result = analyzer.analyze(sector_stocks[0].code)

        assert result.confidence >= 0.5


@pytest.mark.django_db
class TestSectorRelativeStrength:
    def test_outperformer_high_relative_strength(self, sector_stocks):
        """A stock outperforming the sector should have high relative strength."""
        # Create weaker klines for all stocks first.
        for stock in sector_stocks:
            base_price = 10.0
            klines = []
            for i in range(15):
                d = datetime.date(2025, 1, 1) + timedelta(days=i)
                price = base_price * (1 + 0.002 * i)  # 0.2% daily.
                klines.append(
                    KlineData(
                        stock=stock,
                        date=d,
                        open=Decimal(str(round(price * 0.99, 4))),
                        high=Decimal(str(round(price * 1.01, 4))),
                        low=Decimal(str(round(price * 0.98, 4))),
                        close=Decimal(str(round(price, 4))),
                        volume=100000,
                        amount=Decimal(str(round(price * 100000, 4))),
                    )
                )
            KlineData.objects.bulk_create(klines)

        # Now delete and recreate the target stock's klines with strong uptrend.
        target = sector_stocks[0]
        KlineData.objects.filter(stock=target).delete()
        base_price = 10.0
        klines = []
        for i in range(15):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            price = base_price * (1 + 0.02 * i)  # 2% daily.
            klines.append(
                KlineData(
                    stock=target,
                    date=d,
                    open=Decimal(str(round(price * 0.99, 4))),
                    high=Decimal(str(round(price * 1.01, 4))),
                    low=Decimal(str(round(price * 0.98, 4))),
                    close=Decimal(str(round(price, 4))),
                    volume=100000,
                    amount=Decimal(str(round(price * 100000, 4))),
                )
            )
        KlineData.objects.bulk_create(klines)

        analyzer = SectorRotationAnalyzer(lookback_days=20)
        result = analyzer.analyze(target.code)
        rs_score = result.details["component_scores"]["relative_strength"]
        assert rs_score > 60, f"Expected high relative strength, got {rs_score}"
