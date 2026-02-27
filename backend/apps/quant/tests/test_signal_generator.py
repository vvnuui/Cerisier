"""Tests for SignalGenerator and TradingSignal."""

import datetime
from decimal import Decimal

import pytest

from apps.quant.analyzers.signal_generator import SignalGenerator, TradingSignal
from apps.quant.analyzers.types import Signal, TradingStyle
from apps.quant.models import KlineData, StockBasic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_scorer_result(
    signal=Signal.BUY,
    score=80.0,
    confidence=0.8,
    style=TradingStyle.SWING,
):
    return {
        "final_score": score,
        "signal": signal,
        "confidence": confidence,
        "style": style,
        "explanation": "test",
        "analyzer_results": {},
        "component_scores": {},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stock(db):
    return StockBasic.objects.create(
        code="000001",
        name="\u5e73\u5b89\u94f6\u884c",
        industry="\u94f6\u884c",
        sector="\u91d1\u878d",
        market="SZ",
        list_date=datetime.date(1991, 4, 3),
        is_active=True,
    )


@pytest.fixture
def kline_data(stock):
    """Create 20 days of kline data with known prices."""
    klines = []
    base_price = 10.0
    for i in range(20):
        d = datetime.date(2025, 1, 1) + datetime.timedelta(days=i)
        price = base_price + i * 0.1  # steady uptrend
        klines.append(
            KlineData(
                stock=stock,
                date=d,
                open=Decimal(str(round(price - 0.05, 4))),
                high=Decimal(str(round(price + 0.2, 4))),
                low=Decimal(str(round(price - 0.2, 4))),
                close=Decimal(str(round(price, 4))),
                volume=100000 + i * 1000,
                amount=Decimal(str(round(price * (100000 + i * 1000), 4))),
            )
        )
    KlineData.objects.bulk_create(klines)
    return klines


# ---------------------------------------------------------------------------
# Test: Generate BUY signal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateBuySignal:
    def test_generate_buy_signal(self, stock, kline_data):
        """BUY signal: stop_loss < entry < take_profit."""
        gen = SignalGenerator()
        result = make_scorer_result(signal=Signal.BUY, score=80.0, confidence=0.8)
        ts = gen.generate("000001", result)

        assert ts.signal == Signal.BUY
        assert ts.stop_loss < ts.entry_price < ts.take_profit
        assert ts.entry_price > 0
        assert ts.position_pct > 0


# ---------------------------------------------------------------------------
# Test: Generate SELL signal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateSellSignal:
    def test_generate_sell_signal(self, stock, kline_data):
        """SELL signal: stop_loss > entry > take_profit."""
        gen = SignalGenerator()
        result = make_scorer_result(signal=Signal.SELL, score=20.0, confidence=0.8)
        ts = gen.generate("000001", result)

        assert ts.signal == Signal.SELL
        assert ts.stop_loss > ts.entry_price > ts.take_profit
        assert ts.entry_price > 0
        assert ts.position_pct > 0


# ---------------------------------------------------------------------------
# Test: Generate HOLD signal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateHoldSignal:
    def test_generate_hold_signal(self, stock, kline_data):
        """HOLD signal with score=50 should have position_pct near 0."""
        gen = SignalGenerator()
        result = make_scorer_result(
            signal=Signal.HOLD, score=50.0, confidence=0.5
        )
        ts = gen.generate("000001", result)

        assert ts.signal == Signal.HOLD
        # score_factor = |50-50|/50 = 0, so position_pct should be 0
        assert ts.position_pct == 0.0


# ---------------------------------------------------------------------------
# Test: No kline data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNoKlineData:
    def test_no_kline_data(self, stock):
        """No kline data returns HOLD with all prices at 0."""
        gen = SignalGenerator()
        result = make_scorer_result(signal=Signal.BUY, score=80.0, confidence=0.8)
        ts = gen.generate("000001", result)

        assert ts.signal == Signal.HOLD
        assert ts.entry_price == 0.0
        assert ts.stop_loss == 0.0
        assert ts.take_profit == 0.0
        assert ts.position_pct == 0.0
        assert ts.confidence == 0.0
        assert "No price data" in ts.explanation


# ---------------------------------------------------------------------------
# Test: ATR calculation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAtrCalculation:
    def test_atr_calculation(self, stock, kline_data):
        """Verify ATR calculation with known values.

        All klines have high-low range of 0.40 and steady 0.1 steps.
        For a steady uptrend with constant range, TR ~ high-low = 0.40.
        """
        gen = SignalGenerator(atr_period=14)
        # Fetch klines ordered newest-first (same as generate does)
        klines = list(
            KlineData.objects.filter(stock_id="000001").order_by("-date")[:30]
        )
        atr = gen._calculate_atr(klines)

        # Each candle: high = price + 0.2, low = price - 0.2 => range = 0.4
        # prev_close to current high/low also ~0.4 due to 0.1 step
        # TR = max(0.4, |high - prev_close|, |low - prev_close|)
        # high - prev_close = (price + 0.2) - (price - 0.1) = 0.3
        # |low - prev_close| = |(price - 0.2) - (price - 0.1)| = 0.1
        # TR = max(0.4, 0.3, 0.1) = 0.4
        assert abs(atr - 0.4) < 0.01

    def test_atr_single_candle_fallback(self, stock):
        """Single candle ATR falls back to high-low."""
        KlineData.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 1),
            open=Decimal("10.0000"),
            high=Decimal("10.5000"),
            low=Decimal("9.5000"),
            close=Decimal("10.2000"),
            volume=100000,
            amount=Decimal("1020000.0000"),
        )
        gen = SignalGenerator()
        klines = list(
            KlineData.objects.filter(stock_id="000001").order_by("-date")[:30]
        )
        atr = gen._calculate_atr(klines)
        assert abs(atr - 1.0) < 0.001  # high(10.5) - low(9.5) = 1.0


# ---------------------------------------------------------------------------
# Test: Stop-loss ATR multiplier varies by style
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStopLossAtrMultiplier:
    def test_stop_loss_atr_multiplier(self, stock, kline_data):
        """Different styles should produce different stop-loss distances."""
        gen = SignalGenerator()
        results = {}
        for style in TradingStyle:
            scorer_result = make_scorer_result(
                signal=Signal.BUY, score=80.0, confidence=0.8, style=style
            )
            ts = gen.generate("000001", scorer_result)
            results[style] = abs(ts.entry_price - ts.stop_loss)

        # ULTRA_SHORT (1.5) < SWING (2.5) < MID_LONG (3.5)
        assert results[TradingStyle.ULTRA_SHORT] < results[TradingStyle.SWING]
        assert results[TradingStyle.SWING] < results[TradingStyle.MID_LONG]


# ---------------------------------------------------------------------------
# Test: Risk-reward ratio
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRiskRewardRatio:
    def test_risk_reward_ratio(self, stock, kline_data):
        """Risk-reward ratio should match TARGET_RR for BUY signals."""
        gen = SignalGenerator()
        for style in TradingStyle:
            scorer_result = make_scorer_result(
                signal=Signal.BUY, score=80.0, confidence=0.8, style=style
            )
            ts = gen.generate("000001", scorer_result)
            expected_rr = gen.TARGET_RR[style]
            assert abs(ts.risk_reward_ratio - expected_rr) < 0.1, (
                f"Style {style}: expected RR ~{expected_rr}, got {ts.risk_reward_ratio}"
            )


# ---------------------------------------------------------------------------
# Test: Position sizing scales with confidence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPositionSizingScalesWithConfidence:
    def test_position_sizing_scales_with_confidence(self, stock, kline_data):
        """Higher confidence should result in a larger position."""
        gen = SignalGenerator()
        ts_low = gen.generate(
            "000001",
            make_scorer_result(signal=Signal.BUY, score=80.0, confidence=0.3),
        )
        ts_high = gen.generate(
            "000001",
            make_scorer_result(signal=Signal.BUY, score=80.0, confidence=0.9),
        )
        assert ts_high.position_pct > ts_low.position_pct


# ---------------------------------------------------------------------------
# Test: Position sizing scales with score
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPositionSizingScalesWithScore:
    def test_position_sizing_scales_with_score(self, stock, kline_data):
        """More extreme score (further from 50) should produce larger position."""
        gen = SignalGenerator()
        ts_mild = gen.generate(
            "000001",
            make_scorer_result(signal=Signal.BUY, score=60.0, confidence=0.8),
        )
        ts_extreme = gen.generate(
            "000001",
            make_scorer_result(signal=Signal.BUY, score=95.0, confidence=0.8),
        )
        assert ts_extreme.position_pct > ts_mild.position_pct


# ---------------------------------------------------------------------------
# Test: Position max cap
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPositionMaxCap:
    def test_position_max_cap(self, stock, kline_data):
        """Position should not exceed MAX_POSITION_PCT for each style."""
        gen = SignalGenerator()
        for style in TradingStyle:
            scorer_result = make_scorer_result(
                signal=Signal.BUY, score=100.0, confidence=1.0, style=style
            )
            ts = gen.generate("000001", scorer_result)
            max_pct = gen.MAX_POSITION_PCT[style]
            assert ts.position_pct <= max_pct, (
                f"Style {style}: position {ts.position_pct}% > max {max_pct}%"
            )


# ---------------------------------------------------------------------------
# Test: TradingSignal dataclass
# ---------------------------------------------------------------------------


class TestTradingSignalDataclass:
    def test_trading_signal_dataclass(self):
        """TradingSignal has all expected fields."""
        ts = TradingSignal(
            stock_code="000001",
            signal=Signal.BUY,
            score=80.0,
            confidence=0.8,
            style=TradingStyle.SWING,
            entry_price=10.0,
            stop_loss=9.0,
            take_profit=13.0,
            position_pct=5.0,
            risk_reward_ratio=3.0,
            explanation="test signal",
        )
        assert ts.stock_code == "000001"
        assert ts.signal == Signal.BUY
        assert ts.score == 80.0
        assert ts.confidence == 0.8
        assert ts.style == TradingStyle.SWING
        assert ts.entry_price == 10.0
        assert ts.stop_loss == 9.0
        assert ts.take_profit == 13.0
        assert ts.position_pct == 5.0
        assert ts.risk_reward_ratio == 3.0
        assert ts.explanation == "test signal"
        assert ts.details == {}  # default


# ---------------------------------------------------------------------------
# Test: Details include ATR
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetailsIncludeAtr:
    def test_details_include_atr(self, stock, kline_data):
        """Details dict should include ATR and metadata."""
        gen = SignalGenerator()
        ts = gen.generate(
            "000001",
            make_scorer_result(signal=Signal.BUY, score=80.0, confidence=0.8),
        )

        assert "atr" in ts.details
        assert ts.details["atr"] > 0
        assert "current_price" in ts.details
        assert ts.details["current_price"] > 0
        assert "stop_loss_atr_mult" in ts.details
        assert "target_rr" in ts.details
