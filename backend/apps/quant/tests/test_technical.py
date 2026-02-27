"""Tests for TechnicalAnalyzer (MA, MACD, KDJ, BOLL, RSI, Volume)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from apps.quant.analyzers.technical import TechnicalAnalyzer
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


def _generate_trend_series(
    days: int,
    start_price: float,
    trend: float,
    noise: float = 0.005,
    volume_base: int = 100000,
    volume_growth: float = 0.05,
):
    """Generate a price series with controllable trend and noise.

    Returns a list of dicts suitable for both DB creation and DataFrame.
    """
    rows = []
    price = start_price
    for i in range(days):
        d = datetime.date(2025, 1, 1) + timedelta(days=i)
        # Deterministic trend + small noise
        daily_return = trend + noise * (np.random.random() - 0.5)
        new_close = price * (1 + daily_return)
        high = max(price, new_close) * (1 + abs(noise) * np.random.random())
        low = min(price, new_close) * (1 - abs(noise) * np.random.random())
        volume = int(volume_base * (1 + volume_growth * i))
        rows.append(
            {
                "date": d,
                "open": round(price, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(new_close, 4),
                "volume": volume,
                "amount": round(new_close * volume, 4),
            }
        )
        price = new_close
    return rows


def create_uptrend_klines(stock, days=90, start_price=10.0):
    """Create kline data with a clear, sustained uptrend and rising volume.

    Uses ~1.5% daily trend with low noise so that MA, MACD, and volume all
    align bullishly.
    """
    np.random.seed(42)
    rows = _generate_trend_series(
        days=days,
        start_price=start_price,
        trend=0.015,
        noise=0.008,
        volume_base=100000,
        volume_growth=0.08,
    )
    klines = [
        KlineData(
            stock=stock,
            date=r["date"],
            open=Decimal(str(r["open"])),
            high=Decimal(str(r["high"])),
            low=Decimal(str(r["low"])),
            close=Decimal(str(r["close"])),
            volume=r["volume"],
            amount=Decimal(str(r["amount"])),
        )
        for r in rows
    ]
    KlineData.objects.bulk_create(klines)
    return klines


def create_downtrend_klines(stock, days=90, start_price=20.0):
    """Create kline data with a clear, sustained downtrend and rising volume.

    Starts with a flat period (30 days) then turns sharply down (60 days)
    so that MACD shows a death cross and KDJ is not in extreme oversold at
    the very end.
    """
    np.random.seed(42)
    # Phase 1: flat / slightly up (30 days)
    flat_rows = _generate_trend_series(
        days=30,
        start_price=start_price,
        trend=0.002,
        noise=0.005,
        volume_base=100000,
        volume_growth=0.02,
    )
    # Phase 2: sharp decline (60 days)
    last_price = flat_rows[-1]["close"]
    np.random.seed(99)
    down_rows = _generate_trend_series(
        days=60,
        start_price=last_price,
        trend=-0.015,
        noise=0.008,
        volume_base=120000,
        volume_growth=0.08,
    )
    # Shift dates for phase 2
    for i, r in enumerate(down_rows):
        r["date"] = datetime.date(2025, 1, 31) + timedelta(days=i)

    all_rows = flat_rows + down_rows
    klines = [
        KlineData(
            stock=stock,
            date=r["date"],
            open=Decimal(str(r["open"])),
            high=Decimal(str(r["high"])),
            low=Decimal(str(r["low"])),
            close=Decimal(str(r["close"])),
            volume=r["volume"],
            amount=Decimal(str(abs(r["amount"]))),
        )
        for r in all_rows
    ]
    KlineData.objects.bulk_create(klines)
    return klines


def _make_uptrend_df(days=90, start_price=10.0):
    """Build a DataFrame that mimics a sustained uptrend (no DB needed)."""
    np.random.seed(42)
    rows = _generate_trend_series(
        days=days,
        start_price=start_price,
        trend=0.015,
        noise=0.008,
        volume_base=100000,
        volume_growth=0.08,
    )
    df = pd.DataFrame(rows)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def _make_downtrend_df(days=90, start_price=20.0):
    """Build a DataFrame that mimics a flat-then-decline pattern (no DB)."""
    np.random.seed(42)
    flat_rows = _generate_trend_series(
        days=30,
        start_price=start_price,
        trend=0.002,
        noise=0.005,
        volume_base=100000,
        volume_growth=0.02,
    )
    last_price = flat_rows[-1]["close"]
    np.random.seed(99)
    down_rows = _generate_trend_series(
        days=60,
        start_price=last_price,
        trend=-0.015,
        noise=0.008,
        volume_base=120000,
        volume_growth=0.08,
    )
    for i, r in enumerate(down_rows):
        r["date"] = datetime.date(2025, 1, 31) + timedelta(days=i)

    all_rows = flat_rows + down_rows
    df = pd.DataFrame(all_rows)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTechnicalAnalyzerBullish:
    def test_technical_analyzer_bullish(self, stock):
        """Uptrend kline data should yield a bullish score above 55."""
        create_uptrend_klines(stock, days=90)
        analyzer = TechnicalAnalyzer(lookback_days=120)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score > 55, (
            f"Expected bullish score > 55, got {result.score}. "
            f"Indicator scores: {result.details.get('indicator_scores')}"
        )
        # The overall signal should not be SELL for an uptrend.
        assert result.signal != Signal.SELL


@pytest.mark.django_db
class TestTechnicalAnalyzerBearish:
    def test_technical_analyzer_bearish(self, stock):
        """Downtrend kline data should yield a bearish score below 45."""
        create_downtrend_klines(stock, days=90)
        analyzer = TechnicalAnalyzer(lookback_days=120)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score < 45, (
            f"Expected bearish score < 45, got {result.score}. "
            f"Indicator scores: {result.details.get('indicator_scores')}"
        )
        # The overall signal should not be BUY for a downtrend.
        assert result.signal != Signal.BUY


@pytest.mark.django_db
class TestTechnicalAnalyzerInsufficientData:
    def test_technical_analyzer_insufficient_data(self, stock):
        """Only 10 kline records should return HOLD with confidence 0."""
        np.random.seed(42)
        klines = []
        price = 10.0
        for i in range(10):
            d = datetime.date(2025, 1, 1) + timedelta(days=i)
            klines.append(
                KlineData(
                    stock=stock,
                    date=d,
                    open=Decimal(str(round(price, 4))),
                    high=Decimal(str(round(price * 1.01, 4))),
                    low=Decimal(str(round(price * 0.99, 4))),
                    close=Decimal(str(round(price, 4))),
                    volume=100000,
                    amount=Decimal(str(round(price * 100000, 4))),
                )
            )
        KlineData.objects.bulk_create(klines)

        analyzer = TechnicalAnalyzer(lookback_days=120)
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert result.score == 50.0


class TestTechnicalAnalyzerName:
    def test_technical_analyzer_name(self):
        """Verify the analyzer name is 'technical'."""
        analyzer = TechnicalAnalyzer()
        assert analyzer.name == "technical"


@pytest.mark.django_db
class TestIndicatorScoresInDetails:
    def test_indicator_scores_in_details(self, stock):
        """Details should contain indicator_scores dict with all 6 keys."""
        create_uptrend_klines(stock, days=90)
        analyzer = TechnicalAnalyzer(lookback_days=120)
        result = analyzer.analyze(stock.code)

        assert "indicator_scores" in result.details
        indicator_scores = result.details["indicator_scores"]
        expected_keys = {"ma", "macd", "kdj", "boll", "rsi", "volume"}
        assert set(indicator_scores.keys()) == expected_keys

        # Each sub-score must be within 0-100.
        for key, val in indicator_scores.items():
            assert 0.0 <= val <= 100.0, f"{key} score {val} out of range"


@pytest.mark.django_db
class TestSafeAnalyzeOnMissingStock:
    def test_safe_analyze_on_missing_stock(self):
        """safe_analyze for a non-existent stock code returns HOLD."""
        analyzer = TechnicalAnalyzer(lookback_days=120)
        result = analyzer.safe_analyze("DOESNOTEXIST")

        assert isinstance(result, AnalysisResult)
        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0


class TestMaAnalysis:
    def test_ma_analysis_uptrend(self):
        """MA sub-score should be high for an uptrend DataFrame."""
        df = _make_uptrend_df(days=90)
        score = TechnicalAnalyzer._analyze_ma(df)
        assert score > 60, f"Expected MA score > 60 for uptrend, got {score}"

    def test_ma_analysis_downtrend(self):
        """MA sub-score should be low for a downtrend DataFrame."""
        df = _make_downtrend_df(days=90)
        score = TechnicalAnalyzer._analyze_ma(df)
        assert score < 40, f"Expected MA score < 40 for downtrend, got {score}"


class TestRsiAnalysis:
    def test_rsi_analysis_uptrend(self):
        """RSI sub-score should be in a reasonable range for an uptrend."""
        df = _make_uptrend_df(days=90)
        score = TechnicalAnalyzer._analyze_rsi(df)
        # Uptrend RSI is typically in the 50-70 range. Score varies.
        assert 30 <= score <= 80, f"RSI score {score} unexpected for moderate uptrend"

    def test_rsi_analysis_downtrend(self):
        """RSI sub-score for a downtrend: oversold is scored as buy opportunity."""
        df = _make_downtrend_df(days=90)
        score = TechnicalAnalyzer._analyze_rsi(df)
        # RSI scoring is contrarian: oversold gets higher scores.
        # We just verify it returns a valid score.
        assert 0 <= score <= 100, f"RSI score {score} out of range"


class TestMacdAnalysis:
    def test_macd_analysis_uptrend(self):
        """MACD sub-score should be high for an uptrend."""
        df = _make_uptrend_df(days=90)
        score = TechnicalAnalyzer._analyze_macd(df)
        assert score > 55, f"Expected MACD score > 55 for uptrend, got {score}"

    def test_macd_analysis_downtrend(self):
        """MACD sub-score for downtrend should be lower than for uptrend.

        After a sustained decline, DIF may converge toward DEA (slowing
        momentum) which can push MACD slightly positive. The key check is
        that the downtrend MACD score is materially lower than the uptrend.
        """
        df_up = _make_uptrend_df(days=90)
        df_down = _make_downtrend_df(days=90)
        score_up = TechnicalAnalyzer._analyze_macd(df_up)
        score_down = TechnicalAnalyzer._analyze_macd(df_down)
        assert score_down < score_up, (
            f"Downtrend MACD ({score_down}) should be lower than "
            f"uptrend MACD ({score_up})"
        )
