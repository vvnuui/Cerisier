"""Tests for the paper trading simulator engine."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.quant.models import (
    KlineData,
    PerformanceMetric,
    Portfolio,
    Position,
    StockBasic,
    Trade,
)
from apps.quant.simulator import (
    InsufficientFundsError,
    InsufficientSharesError,
    SimulatorEngine,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="trader", email="t@e.com", password="pass123"
    )


@pytest.fixture
def stock(db):
    return StockBasic.objects.create(
        code="000001",
        name="平安银行",
        industry="银行",
        sector="金融",
        market="SZ",
        is_active=True,
    )


@pytest.fixture
def stock2(db):
    return StockBasic.objects.create(
        code="600519",
        name="贵州茅台",
        industry="白酒",
        sector="消费",
        market="SH",
        is_active=True,
    )


@pytest.fixture
def portfolio(user):
    return Portfolio.objects.create(
        user=user,
        name="Test Portfolio",
        initial_capital=Decimal("1000000"),
        cash_balance=Decimal("1000000"),
    )


@pytest.fixture
def engine(portfolio):
    return SimulatorEngine(portfolio)


# ---------------------------------------------------------------------------
# Buy tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBuy:
    def test_buy_basic(self, engine, stock):
        """Buy 100 shares, verify trade created, cash deducted, position
        created."""
        price = Decimal("10.00")
        trade = engine.buy(stock.code, 100, price, reason="test buy")

        # Trade record
        assert trade.trade_type == Trade.BUY
        assert trade.shares == 100
        assert trade.price == price
        assert trade.amount == Decimal("1000.00")
        assert trade.commission >= Decimal("5.00")
        assert trade.reason == "test buy"

        # Position
        position = Position.objects.get(
            portfolio=engine.portfolio, stock=stock
        )
        assert position.shares == 100
        assert position.avg_cost == price
        assert position.current_price == price

        # Cash deducted
        engine.portfolio.refresh_from_db()
        expected_cash = Decimal("1000000") - trade.amount - trade.commission
        assert engine.portfolio.cash_balance == expected_cash

    def test_buy_updates_existing_position(self, engine, stock):
        """Buy twice, verify weighted average cost."""
        engine.buy(stock.code, 100, Decimal("10.00"))
        engine.buy(stock.code, 200, Decimal("12.00"))

        position = Position.objects.get(
            portfolio=engine.portfolio, stock=stock
        )
        assert position.shares == 300

        # Weighted avg: (100*10 + 200*12) / 300 = 3400/300 = 11.3333
        expected_avg = ((100 * Decimal("10.00") + 200 * Decimal("12.00"))
                        / 300).quantize(Decimal("0.0001"))
        assert position.avg_cost == expected_avg

    def test_buy_insufficient_funds(self, engine, stock):
        """Raise InsufficientFundsError when cash is insufficient."""
        with pytest.raises(InsufficientFundsError):
            # Try to buy for more than 1M
            engine.buy(stock.code, 1000000, Decimal("1100.00"))

    def test_buy_zero_shares(self, engine, stock):
        """Raise ValueError when shares <= 0."""
        with pytest.raises(ValueError, match="Shares must be positive"):
            engine.buy(stock.code, 0, Decimal("10.00"))

    def test_buy_negative_shares(self, engine, stock):
        """Raise ValueError when shares are negative."""
        with pytest.raises(ValueError, match="Shares must be positive"):
            engine.buy(stock.code, -100, Decimal("10.00"))

    def test_buy_commission_calculated(self, engine, stock):
        """Commission is at least MIN_COMMISSION (5 yuan)."""
        # Small trade: 100 * 1.00 = 100 yuan -> commission = 100*0.00025 =
        # 0.03, but min is 5
        trade = engine.buy(stock.code, 100, Decimal("1.00"))
        assert trade.commission == Decimal("5.00")

    def test_buy_commission_large_trade(self, engine, stock):
        """Commission calculated correctly for large trade."""
        # 10000 * 100.00 = 1_000_000 yuan -> commission = 1000000*0.00025
        # = 250
        trade = engine.buy(stock.code, 1000, Decimal("100.00"))
        expected_commission = (
            Decimal("100000") * Decimal("0.00025")
        ).quantize(Decimal("0.01"))
        assert trade.commission == expected_commission
        assert trade.commission == Decimal("25.00")


# ---------------------------------------------------------------------------
# Sell tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSell:
    def test_sell_basic(self, engine, stock):
        """Buy then sell all, verify cash returned, position removed."""
        buy_trade = engine.buy(stock.code, 100, Decimal("10.00"))
        sell_trade = engine.sell(stock.code, 100, Decimal("12.00"))

        assert sell_trade.trade_type == Trade.SELL
        assert sell_trade.shares == 100
        assert sell_trade.price == Decimal("12.00")
        assert sell_trade.amount == Decimal("1200.00")

        # Position should be deleted
        assert not Position.objects.filter(
            portfolio=engine.portfolio, stock=stock
        ).exists()

        # Cash: start - buy cost + sell proceeds
        engine.portfolio.refresh_from_db()
        expected_cash = (
            Decimal("1000000")
            - buy_trade.amount
            - buy_trade.commission
            + sell_trade.amount
            - sell_trade.commission
        )
        assert engine.portfolio.cash_balance == expected_cash

    def test_sell_partial(self, engine, stock):
        """Sell part of position, verify remaining shares."""
        engine.buy(stock.code, 300, Decimal("10.00"))
        engine.sell(stock.code, 100, Decimal("12.00"))

        position = Position.objects.get(
            portfolio=engine.portfolio, stock=stock
        )
        assert position.shares == 200
        assert position.current_price == Decimal("12.00")

    def test_sell_insufficient_shares(self, engine, stock):
        """Raise InsufficientSharesError when selling more than held."""
        engine.buy(stock.code, 100, Decimal("10.00"))
        with pytest.raises(InsufficientSharesError, match="Have 100"):
            engine.sell(stock.code, 200, Decimal("12.00"))

    def test_sell_no_position(self, engine, stock):
        """Raise InsufficientSharesError when no position exists."""
        with pytest.raises(
            InsufficientSharesError, match="No position"
        ):
            engine.sell(stock.code, 100, Decimal("12.00"))

    def test_sell_zero_shares(self, engine, stock):
        """Raise ValueError when shares <= 0."""
        with pytest.raises(ValueError, match="Shares must be positive"):
            engine.sell(stock.code, 0, Decimal("12.00"))

    def test_sell_commission_deducted(self, engine, stock):
        """Net proceeds = amount - commission."""
        engine.buy(stock.code, 100, Decimal("10.00"))

        cash_before_sell = engine.portfolio.cash_balance
        sell_trade = engine.sell(stock.code, 100, Decimal("12.00"))

        engine.portfolio.refresh_from_db()
        expected_cash = cash_before_sell + sell_trade.amount - sell_trade.commission
        assert engine.portfolio.cash_balance == expected_cash


# ---------------------------------------------------------------------------
# Portfolio summary tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPortfolioSummary:
    def test_get_portfolio_summary(self, engine, stock):
        """Buy stocks, verify summary dict keys and values."""
        engine.buy(stock.code, 100, Decimal("10.00"))

        summary = engine.get_portfolio_summary()

        assert "portfolio_id" in summary
        assert "name" in summary
        assert "cash_balance" in summary
        assert "total_market_value" in summary
        assert "total_value" in summary
        assert "initial_capital" in summary
        assert "total_return_pct" in summary
        assert "total_unrealized_pnl" in summary
        assert "position_count" in summary
        assert "positions" in summary

        assert summary["position_count"] == 1
        assert summary["name"] == "Test Portfolio"
        assert summary["initial_capital"] == 1000000.0

        # Check position details
        pos = summary["positions"][0]
        assert pos["stock_code"] == stock.code
        assert pos["stock_name"] == "平安银行"
        assert pos["shares"] == 100

    def test_portfolio_summary_multiple_positions(
        self, engine, stock, stock2
    ):
        """Two stocks in portfolio."""
        engine.buy(stock.code, 100, Decimal("10.00"))
        engine.buy(stock2.code, 50, Decimal("1800.00"))

        summary = engine.get_portfolio_summary()
        assert summary["position_count"] == 2
        assert len(summary["positions"]) == 2

        stock_codes = {p["stock_code"] for p in summary["positions"]}
        assert stock_codes == {"000001", "600519"}

    def test_portfolio_summary_empty(self, engine):
        """No positions, all cash."""
        summary = engine.get_portfolio_summary()

        assert summary["position_count"] == 0
        assert summary["positions"] == []
        assert summary["cash_balance"] == 1000000.0
        assert summary["total_market_value"] == 0.0
        assert summary["total_value"] == 1000000.0
        assert summary["total_return_pct"] == 0.0
        assert summary["total_unrealized_pnl"] == 0.0


# ---------------------------------------------------------------------------
# Update positions price tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpdatePositionsPrice:
    def test_update_positions_price(self, engine, stock):
        """Create position, add KlineData, verify price updated."""
        engine.buy(stock.code, 100, Decimal("10.00"))

        # Create kline data with a newer price
        KlineData.objects.create(
            stock=stock,
            date=datetime.date(2025, 6, 15),
            open=Decimal("10.00"),
            high=Decimal("12.50"),
            low=Decimal("9.80"),
            close=Decimal("12.00"),
            volume=1000000,
            amount=Decimal("11000000.00"),
        )

        engine.update_positions_price()

        position = Position.objects.get(
            portfolio=engine.portfolio, stock=stock
        )
        assert position.current_price == Decimal("12.00")


# ---------------------------------------------------------------------------
# Performance calculation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCalculatePerformance:
    def test_calculate_performance_first_day(self, engine):
        """First metric created with correct values."""
        metric = engine.calculate_performance(
            as_of_date=datetime.date(2025, 1, 1)
        )

        assert metric.portfolio == engine.portfolio
        assert metric.date == datetime.date(2025, 1, 1)
        assert metric.total_value == Decimal("1000000.00")
        # No change from initial -> 0% daily return
        assert metric.daily_return == Decimal("0.0")
        assert metric.cumulative_return == Decimal("0.0")
        assert metric.max_drawdown == Decimal("0.0")

    def test_calculate_performance_daily_return(self, engine, stock):
        """Two metrics, verify daily return."""
        # Day 1: no trades
        engine.calculate_performance(as_of_date=datetime.date(2025, 1, 1))

        # Buy stock, then calculate Day 2 with position value change
        engine.buy(stock.code, 100, Decimal("10.00"))

        # Update position price to simulate price change
        pos = Position.objects.get(
            portfolio=engine.portfolio, stock=stock
        )
        pos.current_price = Decimal("11.00")
        pos.save()

        metric2 = engine.calculate_performance(
            as_of_date=datetime.date(2025, 1, 2)
        )

        # daily_return should reflect change from day 1 total_value
        assert metric2.date == datetime.date(2025, 1, 2)
        # Total value on day 2: cash + 100*11 = cash + 1100
        # Cash after buy: 1000000 - 1000 - 5 = 998995
        # Total value day 2 = 998995 + 1100 = 1000095
        # Day 1 total = 1000000
        # daily return = (1000095 - 1000000) / 1000000 * 100 = 0.0095%
        assert float(metric2.daily_return) == pytest.approx(0.0095, abs=0.001)

    def test_calculate_performance_max_drawdown(self, engine, stock):
        """Verify drawdown calculation across multiple days."""
        # Day 1: initial
        engine.calculate_performance(as_of_date=datetime.date(2025, 1, 1))

        # Buy stock
        engine.buy(stock.code, 1000, Decimal("10.00"))

        # Day 2: price goes up
        pos = Position.objects.get(
            portfolio=engine.portfolio, stock=stock
        )
        pos.current_price = Decimal("12.00")
        pos.save()
        engine.calculate_performance(as_of_date=datetime.date(2025, 1, 2))

        # Day 3: price drops
        pos.current_price = Decimal("9.00")
        pos.save()
        metric3 = engine.calculate_performance(
            as_of_date=datetime.date(2025, 1, 3)
        )

        # Max drawdown should be positive (percentage)
        assert float(metric3.max_drawdown) > 0


# ---------------------------------------------------------------------------
# Static method tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStaticMethods:
    def test_max_drawdown_static(self):
        """Direct test of _calc_max_drawdown."""
        values = [100.0, 120.0, 90.0, 110.0, 80.0]
        # Peak = 120, trough = 80 later, but biggest DD from peak to
        # trough: 120 -> 90 = 25%, then 120 -> 80... wait, let's trace:
        # 100 -> peak=100, dd=0
        # 120 -> peak=120, dd=0
        # 90 -> peak=120, dd=(120-90)/120*100 = 25%
        # 110 -> peak=120, dd=(120-110)/120*100 = 8.33%
        # 80 -> peak=120, dd=(120-80)/120*100 = 33.33%
        dd = SimulatorEngine._calc_max_drawdown(values)
        assert dd == pytest.approx(33.333, abs=0.01)

    def test_max_drawdown_no_drawdown(self):
        """Always increasing values should have 0 drawdown."""
        values = [100.0, 110.0, 120.0, 130.0]
        dd = SimulatorEngine._calc_max_drawdown(values)
        assert dd == 0.0

    def test_max_drawdown_single_value(self):
        """Single value returns 0."""
        dd = SimulatorEngine._calc_max_drawdown([100.0])
        assert dd == 0.0

    def test_sharpe_ratio_static(self):
        """Direct test of _calc_sharpe_ratio with sufficient data."""
        # 10 daily returns of 1%
        returns = [1.0] * 10
        sharpe = SimulatorEngine._calc_sharpe_ratio(returns)
        # With constant returns, std should be 0 -> None
        assert sharpe is None

    def test_sharpe_ratio_with_variance(self):
        """Sharpe ratio with varying returns."""
        returns = [1.0, -0.5, 0.8, -0.3, 1.2, 0.2, -0.1, 0.9, 0.5, -0.2]
        sharpe = SimulatorEngine._calc_sharpe_ratio(returns)
        assert sharpe is not None
        # Should be a positive number given mostly positive returns
        assert isinstance(sharpe, float)

    def test_sharpe_ratio_insufficient_data(self):
        """Returns None with < 5 data points."""
        returns = [1.0, 2.0, 3.0]
        sharpe = SimulatorEngine._calc_sharpe_ratio(returns)
        assert sharpe is None

    def test_sharpe_ratio_exactly_five(self):
        """Five data points should compute."""
        returns = [1.0, -0.5, 0.8, -0.3, 1.2]
        sharpe = SimulatorEngine._calc_sharpe_ratio(returns)
        assert sharpe is not None


# ---------------------------------------------------------------------------
# Win rate tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWinRate:
    def test_win_rate_basic(self, engine, stock):
        """Buy low, sell high = 100% win rate."""
        engine.buy(stock.code, 100, Decimal("10.00"))
        engine.sell(stock.code, 100, Decimal("15.00"))

        sell_trades = Trade.objects.filter(
            portfolio=engine.portfolio, trade_type=Trade.SELL
        )
        win_rate = SimulatorEngine._calc_win_rate(sell_trades)
        assert win_rate == 100.0

    def test_win_rate_loss(self, engine, stock):
        """Buy high, sell low = 0% win rate."""
        engine.buy(stock.code, 100, Decimal("15.00"))
        engine.sell(stock.code, 100, Decimal("10.00"))

        sell_trades = Trade.objects.filter(
            portfolio=engine.portfolio, trade_type=Trade.SELL
        )
        win_rate = SimulatorEngine._calc_win_rate(sell_trades)
        assert win_rate == 0.0

    def test_win_rate_mixed(self, engine, stock, stock2):
        """One win, one loss = 50% win rate."""
        # Stock 1: buy low sell high (win)
        engine.buy(stock.code, 100, Decimal("10.00"))
        engine.sell(stock.code, 100, Decimal("15.00"))

        # Stock 2: buy high sell low (loss)
        engine.buy(stock2.code, 100, Decimal("1800.00"))
        engine.sell(stock2.code, 100, Decimal("1500.00"))

        sell_trades = Trade.objects.filter(
            portfolio=engine.portfolio, trade_type=Trade.SELL
        )
        win_rate = SimulatorEngine._calc_win_rate(sell_trades)
        assert win_rate == 50.0

    def test_win_rate_no_sells(self, engine, stock):
        """Returns None when there are no sell trades."""
        engine.buy(stock.code, 100, Decimal("10.00"))

        sell_trades = Trade.objects.filter(
            portfolio=engine.portfolio, trade_type=Trade.SELL
        )
        win_rate = SimulatorEngine._calc_win_rate(sell_trades)
        assert win_rate is None
