"""Tests for experimental analyzers (GameTheory, BehaviorFinance, Macro)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest

from apps.quant.analyzers.experimental import (
    BehaviorFinanceAnalyzer,
    GameTheoryAnalyzer,
    MacroAnalyzer,
)
from apps.quant.analyzers.types import AnalysisResult, Signal
from apps.quant.models import KlineData, StockBasic

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


def create_klines(stock, days=20, start_price=10.0, daily_return=0.01, volume_base=100000):
    """Create kline data with controllable trend."""
    klines = []
    price = start_price
    for i in range(days):
        d = datetime.date(2025, 1, 1) + timedelta(days=i)
        new_price = price * (1 + daily_return)
        klines.append(
            KlineData(
                stock=stock,
                date=d,
                open=Decimal(str(round(price, 4))),
                high=Decimal(str(round(max(price, new_price) * 1.005, 4))),
                low=Decimal(str(round(min(price, new_price) * 0.995, 4))),
                close=Decimal(str(round(new_price, 4))),
                volume=volume_base + i * 5000,
                amount=Decimal(str(round(new_price * (volume_base + i * 5000), 4))),
            )
        )
        price = new_price
    KlineData.objects.bulk_create(klines)
    return klines


# ---------------------------------------------------------------------------
# GameTheoryAnalyzer tests
# ---------------------------------------------------------------------------


class TestGameTheoryName:
    def test_name(self):
        """Verify the analyzer name is 'game_theory'."""
        analyzer = GameTheoryAnalyzer()
        assert analyzer.name == "game_theory"


@pytest.mark.django_db
class TestGameTheoryInsufficientData:
    def test_insufficient_data(self, stock):
        """Less than 10 days should return HOLD with confidence 0."""
        create_klines(stock, days=5)
        analyzer = GameTheoryAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert result.score == 50.0


@pytest.mark.django_db
class TestGameTheoryAnalysis:
    def test_produces_valid_result(self, stock):
        """Should produce a valid AnalysisResult with component scores."""
        create_klines(stock, days=20, daily_return=0.015, volume_base=100000)
        analyzer = GameTheoryAnalyzer()
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert 0 <= result.score <= 100
        assert 0 <= result.confidence <= 1
        assert "component_scores" in result.details

        scores = result.details["component_scores"]
        expected_keys = {"volume_price_divergence", "volume_trend"}
        assert set(scores.keys()) == expected_keys


# ---------------------------------------------------------------------------
# BehaviorFinanceAnalyzer tests
# ---------------------------------------------------------------------------


class TestBehaviorFinanceName:
    def test_name(self):
        """Verify the analyzer name is 'behavior_finance'."""
        analyzer = BehaviorFinanceAnalyzer()
        assert analyzer.name == "behavior_finance"


@pytest.mark.django_db
class TestBehaviorFinanceInsufficientData:
    def test_insufficient_data(self, stock):
        """Less than 10 days should return HOLD with confidence 0."""
        create_klines(stock, days=5)
        analyzer = BehaviorFinanceAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert result.score == 50.0


@pytest.mark.django_db
class TestBehaviorFinanceAnalysis:
    def test_produces_valid_result(self, stock):
        """Should produce a valid AnalysisResult with component scores."""
        create_klines(stock, days=20)
        analyzer = BehaviorFinanceAnalyzer()
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert 0 <= result.score <= 100
        assert 0 <= result.confidence <= 1
        assert "component_scores" in result.details

        scores = result.details["component_scores"]
        expected_keys = {"overreaction", "anchoring"}
        assert set(scores.keys()) == expected_keys


# ---------------------------------------------------------------------------
# MacroAnalyzer tests
# ---------------------------------------------------------------------------


class TestMacroName:
    def test_name(self):
        """Verify the analyzer name is 'macro'."""
        analyzer = MacroAnalyzer()
        assert analyzer.name == "macro"


class TestMacroAlwaysNeutral:
    def test_always_hold(self):
        """MacroAnalyzer always returns HOLD with score=50."""
        analyzer = MacroAnalyzer()
        result = analyzer.analyze("000001")

        assert isinstance(result, AnalysisResult)
        assert result.score == 50.0
        assert result.signal == Signal.HOLD
        assert result.confidence == 0.1
        assert "external data" in result.explanation.lower()

    def test_placeholder_details(self):
        """MacroAnalyzer returns placeholder status in details."""
        analyzer = MacroAnalyzer()
        result = analyzer.analyze("ANY_CODE")

        assert result.details == {"status": "placeholder"}
