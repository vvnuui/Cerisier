"""Tests for FundamentalAnalyzer (PE/PB valuation, ROE, growth, margins)."""

import datetime
from decimal import Decimal

import pytest

from apps.quant.analyzers.fundamental import FundamentalAnalyzer
from apps.quant.analyzers.types import AnalysisResult, Signal
from apps.quant.models import FinancialReport, StockBasic

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


def create_reports(
    stock,
    pe=15,
    pb=1.5,
    roe=12,
    revenue=1000000,
    net_profit=100000,
    gross_margin=30,
    debt_ratio=45,
):
    """Create 2 quarterly reports for testing.

    The earlier period (Q2) has ~10% less revenue and ~15% less net_profit
    than the later period (Q3) to simulate growth.
    """
    FinancialReport.objects.create(
        stock=stock,
        period="2025Q2",
        pe_ratio=pe,
        pb_ratio=pb,
        roe=roe,
        revenue=Decimal(str(revenue * 0.9)),
        net_profit=Decimal(str(net_profit * 0.85)),
        gross_margin=gross_margin,
        debt_ratio=debt_ratio,
    )
    FinancialReport.objects.create(
        stock=stock,
        period="2025Q3",
        pe_ratio=pe,
        pb_ratio=pb,
        roe=roe,
        revenue=Decimal(str(revenue)),
        net_profit=Decimal(str(net_profit)),
        gross_margin=gross_margin,
        debt_ratio=debt_ratio,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFundamentalBullish:
    def test_fundamental_bullish(self, stock):
        """Good PE, high ROE, growth, high margin -> BUY-ish score."""
        create_reports(
            stock,
            pe=8,          # very cheap
            pb=0.8,        # PB bonus
            roe=22,        # excellent
            revenue=2000000,
            net_profit=400000,
            gross_margin=55,  # high margin
            debt_ratio=30,    # low debt bonus
        )
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score > 70, (
            f"Expected bullish score > 70, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal == Signal.BUY


@pytest.mark.django_db
class TestFundamentalBearish:
    def test_fundamental_bearish(self, stock):
        """High PE, low ROE, declining revenue, low margin -> SELL-ish score."""
        # Create Q2 with higher numbers, Q3 with lower -> decline.
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q2",
            pe_ratio=50,
            pb_ratio=5,
            roe=3,
            revenue=Decimal("2000000"),
            net_profit=Decimal("200000"),
            gross_margin=Decimal("10"),
            debt_ratio=Decimal("75"),
        )
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            pe_ratio=55,
            pb_ratio=6,
            roe=2,
            revenue=Decimal("1500000"),   # decline
            net_profit=Decimal("100000"),  # decline
            gross_margin=Decimal("8"),
            debt_ratio=Decimal("80"),
        )

        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score < 30, (
            f"Expected bearish score < 30, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal == Signal.SELL


@pytest.mark.django_db
class TestFundamentalNoData:
    def test_fundamental_no_data(self, stock):
        """No reports exist -> HOLD with confidence=0."""
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert result.score == 50.0


class TestFundamentalName:
    def test_fundamental_name(self):
        """Verify the analyzer name is 'fundamental'."""
        analyzer = FundamentalAnalyzer()
        assert analyzer.name == "fundamental"
        assert "PE/PB" in analyzer.description or "valuation" in analyzer.description


@pytest.mark.django_db
class TestValuationScoring:
    def test_pe_very_cheap(self, stock):
        """PE < 10 should score 90, PB < 1 adds bonus."""
        create_reports(stock, pe=8, pb=0.8)
        analyzer = FundamentalAnalyzer()
        report = FinancialReport.objects.filter(stock=stock).order_by("-period").first()
        score = analyzer._score_valuation(report)
        assert score == 100.0  # 90 + 10 (PB bonus), clamped at 100

    def test_pe_cheap(self, stock):
        """PE 10-15 should score 75."""
        create_reports(stock, pe=12, pb=2.0)
        analyzer = FundamentalAnalyzer()
        report = FinancialReport.objects.filter(stock=stock).order_by("-period").first()
        score = analyzer._score_valuation(report)
        assert score == 75.0

    def test_pe_moderate(self, stock):
        """PE 15-25 should score 55."""
        create_reports(stock, pe=20, pb=2.0)
        analyzer = FundamentalAnalyzer()
        report = FinancialReport.objects.filter(stock=stock).order_by("-period").first()
        score = analyzer._score_valuation(report)
        assert score == 55.0

    def test_pe_expensive(self, stock):
        """PE 25-40 should score 35."""
        create_reports(stock, pe=30, pb=2.0)
        analyzer = FundamentalAnalyzer()
        report = FinancialReport.objects.filter(stock=stock).order_by("-period").first()
        score = analyzer._score_valuation(report)
        assert score == 35.0

    def test_pe_very_expensive(self, stock):
        """PE > 40 should score 15."""
        create_reports(stock, pe=50, pb=2.0)
        analyzer = FundamentalAnalyzer()
        report = FinancialReport.objects.filter(stock=stock).order_by("-period").first()
        score = analyzer._score_valuation(report)
        assert score == 15.0

    def test_pb_bonus_applied(self, stock):
        """PB < 1 gives +10 bonus on top of PE score."""
        create_reports(stock, pe=12, pb=0.9)
        analyzer = FundamentalAnalyzer()
        report = FinancialReport.objects.filter(stock=stock).order_by("-period").first()
        score = analyzer._score_valuation(report)
        assert score == 85.0  # 75 + 10

    def test_pe_none_returns_neutral(self, stock):
        """When PE is null, valuation score is neutral (50)."""
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            pe_ratio=None,
            pb_ratio=None,
        )
        report = FinancialReport.objects.get(stock=stock, period="2025Q3")
        score = FundamentalAnalyzer._score_valuation(report)
        assert score == 50.0


@pytest.mark.django_db
class TestGrowthCalculation:
    def test_growth_positive(self, stock):
        """Revenue and profit growing > 20% should score high."""
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q2",
            revenue=Decimal("1000000"),
            net_profit=Decimal("100000"),
        )
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            revenue=Decimal("1300000"),   # +30%
            net_profit=Decimal("130000"),  # +30%
        )
        reports = list(
            FinancialReport.objects.filter(stock=stock).order_by("-period")[:4]
        )
        score = FundamentalAnalyzer._score_growth(reports)
        assert score == 85.0  # both > 20% growth -> 85

    def test_growth_moderate(self, stock):
        """Revenue/profit growing 10-20% should score 70."""
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q2",
            revenue=Decimal("1000000"),
            net_profit=Decimal("100000"),
        )
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            revenue=Decimal("1150000"),   # +15%
            net_profit=Decimal("115000"),  # +15%
        )
        reports = list(
            FinancialReport.objects.filter(stock=stock).order_by("-period")[:4]
        )
        score = FundamentalAnalyzer._score_growth(reports)
        assert score == 70.0

    def test_growth_decline(self, stock):
        """Revenue and profit declining should score 25."""
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q2",
            revenue=Decimal("1000000"),
            net_profit=Decimal("100000"),
        )
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            revenue=Decimal("800000"),   # -20%
            net_profit=Decimal("70000"),  # -30%
        )
        reports = list(
            FinancialReport.objects.filter(stock=stock).order_by("-period")[:4]
        )
        score = FundamentalAnalyzer._score_growth(reports)
        assert score == 25.0  # both declining -> 25

    def test_growth_single_report(self, stock):
        """Only one report -> neutral growth score (50)."""
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            revenue=Decimal("1000000"),
            net_profit=Decimal("100000"),
        )
        reports = list(
            FinancialReport.objects.filter(stock=stock).order_by("-period")[:4]
        )
        score = FundamentalAnalyzer._score_growth(reports)
        assert score == 50.0


@pytest.mark.django_db
class TestPartialData:
    def test_partial_data_still_works(self, stock):
        """Some fields null; analyzer should still produce a valid result
        with lower confidence."""
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q2",
            pe_ratio=15,
            pb_ratio=None,
            roe=None,
            revenue=None,
            net_profit=None,
            gross_margin=None,
            debt_ratio=None,
        )
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            pe_ratio=14,
            pb_ratio=None,
            roe=None,
            revenue=None,
            net_profit=None,
            gross_margin=None,
            debt_ratio=None,
        )

        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert 0 <= result.score <= 100
        # Only pe_ratio is non-null in each report: 2 out of 14 fields.
        assert result.confidence < 0.5, (
            f"Expected low confidence with mostly null data, got {result.confidence}"
        )
        # Should not crash.
        assert result.signal in (Signal.BUY, Signal.SELL, Signal.HOLD)

    def test_all_fields_present_high_confidence(self, stock):
        """All fields present in all reports -> confidence near 1.0."""
        create_reports(
            stock,
            pe=15,
            pb=1.5,
            roe=12,
            revenue=1000000,
            net_profit=100000,
            gross_margin=30,
            debt_ratio=45,
        )
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.confidence == 1.0


@pytest.mark.django_db
class TestComponentScoresInDetails:
    def test_component_scores_in_details(self, stock):
        """Details should contain component_scores dict with all 4 keys."""
        create_reports(stock)
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(stock.code)

        assert "component_scores" in result.details
        scores = result.details["component_scores"]
        expected_keys = {"valuation", "quality", "growth", "margins"}
        assert set(scores.keys()) == expected_keys

        for key, val in scores.items():
            assert 0.0 <= val <= 100.0, f"{key} score {val} out of range"
