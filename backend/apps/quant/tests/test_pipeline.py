"""Tests for analysis pipeline Celery tasks."""

import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from apps.quant.analyzers.signal_generator import TradingSignal
from apps.quant.analyzers.types import Signal, TradingStyle
from apps.quant.models import KlineData, MoneyFlow, StockBasic
from apps.quant.tasks import analyze_single_stock, run_analysis_pipeline

# Patch targets: lazy imports inside the task functions resolve via
# ``from .analyzers import …``, which goes through the analyzers package.
_SCORER_PATCH = "apps.quant.analyzers.MultiFactorScorer"
_SIGGEN_PATCH = "apps.quant.analyzers.SignalGenerator"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scorer_result(
    signal=Signal.BUY,
    score=80.0,
    confidence=0.8,
    style=TradingStyle.SWING,
    explanation="test explanation",
    component_scores=None,
):
    """Create a scorer result dict matching MultiFactorScorer.score() output."""
    return {
        "final_score": score,
        "signal": signal,
        "confidence": confidence,
        "style": style,
        "explanation": explanation,
        "analyzer_results": {},
        "component_scores": component_scores or {"technical": 20.0, "fundamental": 12.0},
    }


def _make_trading_signal(
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
):
    """Create a TradingSignal dataclass instance."""
    return TradingSignal(
        stock_code=stock_code,
        signal=signal,
        score=score,
        confidence=confidence,
        style=style,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_pct=position_pct,
        risk_reward_ratio=risk_reward_ratio,
        explanation="test signal",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def three_stocks(db):
    """Create 3 active StockBasic records."""
    stocks = []
    for code, name, industry in [
        ("000001", "Stock A", "Banking"),
        ("000002", "Stock B", "Tech"),
        ("000003", "Stock C", "Energy"),
    ]:
        stocks.append(
            StockBasic.objects.create(
                code=code,
                name=name,
                industry=industry,
                sector="Test",
                market="SZ",
                is_active=True,
            )
        )
    return stocks


@pytest.fixture
def kline_data(three_stocks):
    """Create 30 days of kline data per stock."""
    klines = []
    base_price = 10.0
    for stock in three_stocks:
        for i in range(30):
            d = datetime.date(2025, 1, 1) + datetime.timedelta(days=i)
            price = base_price + i * 0.1
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
                    turnover=Decimal(str(round(1.5 + i * 0.01, 4))),
                    change_pct=Decimal(str(round(0.5 + i * 0.02, 4))),
                )
            )
    KlineData.objects.bulk_create(klines)
    return klines


@pytest.fixture
def money_flow_data(three_stocks):
    """Create some MoneyFlow records per stock."""
    flows = []
    for stock in three_stocks:
        for i in range(10):
            d = datetime.date(2025, 1, 20) + datetime.timedelta(days=i)
            flows.append(
                MoneyFlow(
                    stock=stock,
                    date=d,
                    main_net=Decimal(str(round(1000000 * (0.5 - i * 0.1), 4))),
                    huge_net=Decimal(str(round(500000 * (0.3 - i * 0.05), 4))),
                    big_net=Decimal(str(round(300000 * (0.2 - i * 0.03), 4))),
                    mid_net=Decimal(str(round(100000 * (0.1 + i * 0.02), 4))),
                    small_net=Decimal(str(round(50000 * (0.1 + i * 0.01), 4))),
                )
            )
    MoneyFlow.objects.bulk_create(flows)
    return flows


# ---------------------------------------------------------------------------
# Test: run_analysis_pipeline basic
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRunAnalysisPipelineBasic:
    def test_run_analysis_pipeline_basic(self, three_stocks, kline_data):
        """Pipeline returns correct structure with expected keys."""
        mock_scorer = MagicMock()
        mock_signal_gen = MagicMock()

        # Configure mock scorer to return BUY for stock A, HOLD for B, SELL for C
        def mock_score(code):
            if code == "000001":
                return _make_scorer_result(signal=Signal.BUY, score=85.0)
            elif code == "000002":
                return _make_scorer_result(signal=Signal.HOLD, score=50.0)
            else:
                return _make_scorer_result(signal=Signal.SELL, score=20.0)

        mock_scorer.score.side_effect = mock_score

        # Configure mock signal generator
        def mock_generate(code, result):
            return _make_trading_signal(stock_code=code, signal=result["signal"])

        mock_signal_gen.generate.side_effect = mock_generate

        with patch(_SCORER_PATCH, return_value=mock_scorer), \
             patch(_SIGGEN_PATCH, return_value=mock_signal_gen):
            result = run_analysis_pipeline("swing")

        assert result["style"] == "swing"
        assert result["total_analyzed"] == 3
        assert result["buy_count"] == 1
        assert result["sell_count"] == 1
        assert result["hold_count"] == 1
        assert result["errors"] == 0
        assert isinstance(result["top_picks"], list)
        assert isinstance(result["top_sells"], list)


# ---------------------------------------------------------------------------
# Test: Style string parsing
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRunAnalysisPipelineStyleParsing:
    @pytest.mark.parametrize(
        "style_str,expected_style",
        [
            ("ultra_short", TradingStyle.ULTRA_SHORT),
            ("swing", TradingStyle.SWING),
            ("mid_long", TradingStyle.MID_LONG),
        ],
    )
    def test_run_analysis_pipeline_style_parsing(self, style_str, expected_style, db):
        """Different style strings should be parsed to the correct TradingStyle enum."""
        mock_scorer_cls = MagicMock()
        mock_scorer_instance = MagicMock()
        mock_scorer_cls.return_value = mock_scorer_instance

        with patch(_SCORER_PATCH, mock_scorer_cls), \
             patch(_SIGGEN_PATCH):
            run_analysis_pipeline(style_str)

        mock_scorer_cls.assert_called_once_with(style=expected_style)


# ---------------------------------------------------------------------------
# Test: Handles errors gracefully
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRunAnalysisPipelineHandlesErrors:
    def test_run_analysis_pipeline_handles_errors(self, three_stocks, kline_data):
        """When scorer raises on one stock, errors count increments."""
        mock_scorer = MagicMock()
        mock_signal_gen = MagicMock()

        def mock_score(code):
            if code == "000002":
                raise ValueError("Test analysis failure")
            return _make_scorer_result(signal=Signal.BUY, score=80.0)

        mock_scorer.score.side_effect = mock_score
        mock_signal_gen.generate.return_value = _make_trading_signal()

        with patch(_SCORER_PATCH, return_value=mock_scorer), \
             patch(_SIGGEN_PATCH, return_value=mock_signal_gen):
            result = run_analysis_pipeline("swing")

        assert result["errors"] == 1
        assert result["total_analyzed"] == 2  # 3 stocks - 1 error


# ---------------------------------------------------------------------------
# Test: Results sorted by score descending
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRunAnalysisPipelineSortsByScore:
    def test_run_analysis_pipeline_sorts_by_score(self, three_stocks, kline_data):
        """Results should be sorted by score descending."""
        mock_scorer = MagicMock()
        mock_signal_gen = MagicMock()

        scores = {"000001": 60.0, "000002": 90.0, "000003": 75.0}

        def mock_score(code):
            return _make_scorer_result(signal=Signal.BUY, score=scores[code])

        mock_scorer.score.side_effect = mock_score
        mock_signal_gen.generate.return_value = _make_trading_signal()

        with patch(_SCORER_PATCH, return_value=mock_scorer), \
             patch(_SIGGEN_PATCH, return_value=mock_signal_gen):
            result = run_analysis_pipeline("swing")

        top_picks = result["top_picks"]
        assert len(top_picks) == 3
        assert top_picks[0]["score"] == 90.0
        assert top_picks[1]["score"] == 75.0
        assert top_picks[2]["score"] == 60.0


# ---------------------------------------------------------------------------
# Test: Empty stocks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRunAnalysisPipelineEmptyStocks:
    def test_run_analysis_pipeline_empty_stocks(self, db):
        """No active stocks returns empty results."""
        result = run_analysis_pipeline("swing")

        assert result["total_analyzed"] == 0
        assert result["buy_count"] == 0
        assert result["sell_count"] == 0
        assert result["hold_count"] == 0
        assert result["errors"] == 0
        assert result["top_picks"] == []
        assert result["top_sells"] == []


# ---------------------------------------------------------------------------
# Test: analyze_single_stock basic
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAnalyzeSingleStockBasic:
    def test_analyze_single_stock_basic(self, three_stocks, kline_data):
        """Single stock analysis returns a result dict."""
        mock_scorer = MagicMock()
        mock_signal_gen = MagicMock()

        mock_scorer.score.return_value = _make_scorer_result(
            signal=Signal.BUY, score=85.0, confidence=0.9
        )
        mock_signal_gen.generate.return_value = _make_trading_signal(
            stock_code="000001", entry_price=12.9, stop_loss=11.9, take_profit=15.9
        )

        with patch(_SCORER_PATCH, return_value=mock_scorer), \
             patch(_SIGGEN_PATCH, return_value=mock_signal_gen):
            result = analyze_single_stock("000001", "swing")

        assert result["stock_code"] == "000001"
        assert result["style"] == "swing"
        assert result["score"] == 85.0
        assert result["signal"] == "BUY"
        assert result["confidence"] == 0.9
        assert result["entry_price"] == 12.9
        assert result["stop_loss"] == 11.9
        assert result["take_profit"] == 15.9


# ---------------------------------------------------------------------------
# Test: analyze_single_stock return keys
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAnalyzeSingleStockReturnKeys:
    def test_analyze_single_stock_return_keys(self, three_stocks, kline_data):
        """Verify all expected keys in return dict."""
        mock_scorer = MagicMock()
        mock_signal_gen = MagicMock()

        mock_scorer.score.return_value = _make_scorer_result()
        mock_signal_gen.generate.return_value = _make_trading_signal()

        with patch(_SCORER_PATCH, return_value=mock_scorer), \
             patch(_SIGGEN_PATCH, return_value=mock_signal_gen):
            result = analyze_single_stock("000001", "swing")

        expected_keys = {
            "stock_code",
            "style",
            "score",
            "signal",
            "confidence",
            "explanation",
            "entry_price",
            "stop_loss",
            "take_profit",
            "position_pct",
            "risk_reward_ratio",
            "component_scores",
        }
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Test: analyze_single_stock invalid style falls back to SWING
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAnalyzeSingleStockInvalidStyle:
    def test_analyze_single_stock_invalid_style(self, three_stocks, kline_data):
        """Invalid style falls back to SWING."""
        mock_scorer_cls = MagicMock()
        mock_scorer_instance = MagicMock()
        mock_scorer_cls.return_value = mock_scorer_instance
        mock_scorer_instance.score.return_value = _make_scorer_result()

        mock_signal_gen_cls = MagicMock()
        mock_signal_gen_cls.return_value.generate.return_value = _make_trading_signal()

        with patch(_SCORER_PATCH, mock_scorer_cls), \
             patch(_SIGGEN_PATCH, mock_signal_gen_cls):
            analyze_single_stock("000001", "invalid_style")

        mock_scorer_cls.assert_called_once_with(style=TradingStyle.SWING)
