import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.quant.models import (
    PerformanceMetric,
    Portfolio,
    Position,
    StockBasic,
    Trade,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
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
def another_stock(db):
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
        name="测试组合",
        initial_capital=Decimal("1000000.00"),
        cash_balance=Decimal("1000000.00"),
    )


@pytest.fixture
def position(portfolio, stock):
    return Position.objects.create(
        portfolio=portfolio,
        stock=stock,
        shares=1000,
        avg_cost=Decimal("10.5000"),
        current_price=Decimal("11.2000"),
    )


@pytest.fixture
def trade(portfolio, stock):
    return Trade.objects.create(
        portfolio=portfolio,
        stock=stock,
        trade_type=Trade.BUY,
        shares=1000,
        price=Decimal("10.5000"),
        amount=Decimal("10500.00"),
        commission=Decimal("5.25"),
        reason="技术指标买入信号",
    )


@pytest.fixture
def performance_metric(portfolio):
    return PerformanceMetric.objects.create(
        portfolio=portfolio,
        date=datetime.date(2025, 1, 10),
        total_value=Decimal("1050000.00"),
        daily_return=Decimal("0.5000"),
        cumulative_return=Decimal("5.0000"),
        max_drawdown=Decimal("2.0000"),
        sharpe_ratio=Decimal("1.5000"),
        win_rate=Decimal("60.0000"),
    )


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPortfolio:
    def test_create_portfolio(self, portfolio, user):
        """Create portfolio with user, verify fields."""
        p = Portfolio.objects.get(pk=portfolio.pk)
        assert p.user == user
        assert p.name == "测试组合"
        assert p.initial_capital == Decimal("1000000.00")
        assert p.cash_balance == Decimal("1000000.00")
        assert p.is_active is True
        assert p.created_at is not None
        assert p.updated_at is not None

    def test_portfolio_str(self, portfolio, user):
        """__str__ returns name and user."""
        assert str(portfolio) == f"测试组合 ({user})"

    def test_portfolio_default_capital(self, user):
        """Default initial_capital is 1_000_000."""
        p = Portfolio.objects.create(user=user, name="默认资金组合")
        assert p.initial_capital == Decimal("1000000")
        assert p.cash_balance == Decimal("1000000")


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPosition:
    def test_create_position(self, position, portfolio, stock):
        """Create position, verify fields."""
        pos = Position.objects.get(pk=position.pk)
        assert pos.portfolio == portfolio
        assert pos.stock == stock
        assert pos.shares == 1000
        assert pos.avg_cost == Decimal("10.5000")
        assert pos.current_price == Decimal("11.2000")
        assert pos.updated_at is not None

    def test_position_unique_together(self, position, portfolio, stock):
        """Same portfolio+stock is unique."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Position.objects.create(
                    portfolio=portfolio,
                    stock=stock,
                    shares=500,
                    avg_cost=Decimal("9.0000"),
                    current_price=Decimal("9.5000"),
                )

    def test_position_market_value(self, position):
        """market_value = shares * current_price."""
        expected = 1000 * Decimal("11.2000")
        assert position.market_value == expected

    def test_position_cost_basis(self, position):
        """cost_basis = shares * avg_cost."""
        expected = 1000 * Decimal("10.5000")
        assert position.cost_basis == expected

    def test_position_unrealized_pnl(self, position):
        """unrealized_pnl = market_value - cost_basis."""
        market_value = 1000 * Decimal("11.2000")
        cost_basis = 1000 * Decimal("10.5000")
        expected = market_value - cost_basis
        assert position.unrealized_pnl == expected

    def test_position_unrealized_pnl_pct(self, position):
        """unrealized_pnl_pct = percentage calculation."""
        market_value = 1000 * Decimal("11.2000")
        cost_basis = 1000 * Decimal("10.5000")
        pnl = market_value - cost_basis
        expected = float((pnl / cost_basis) * 100)
        assert abs(position.unrealized_pnl_pct - expected) < 0.0001

    def test_position_zero_cost_pnl_pct(self, portfolio, stock):
        """Returns 0 when cost is 0."""
        pos = Position.objects.create(
            portfolio=portfolio,
            stock=stock,
            shares=0,
            avg_cost=Decimal("0.0000"),
            current_price=Decimal("10.0000"),
        )
        assert pos.unrealized_pnl_pct == 0


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTrade:
    def test_create_trade(self, trade, portfolio, stock):
        """Create trade, verify fields."""
        t = Trade.objects.get(pk=trade.pk)
        assert t.portfolio == portfolio
        assert t.stock == stock
        assert t.trade_type == Trade.BUY
        assert t.shares == 1000
        assert t.price == Decimal("10.5000")
        assert t.amount == Decimal("10500.00")
        assert t.commission == Decimal("5.25")
        assert t.reason == "技术指标买入信号"
        assert t.executed_at is not None

    def test_trade_str(self, trade):
        """__str__ format."""
        assert str(trade) == "BUY 000001 x 1000 @ 10.5000"

    def test_trade_ordering(self, portfolio, stock):
        """Ordered by -executed_at (most recent first)."""
        now = timezone.now()
        t1 = Trade.objects.create(
            portfolio=portfolio,
            stock=stock,
            trade_type=Trade.BUY,
            shares=100,
            price=Decimal("10.0000"),
            amount=Decimal("1000.00"),
        )
        t2 = Trade.objects.create(
            portfolio=portfolio,
            stock=stock,
            trade_type=Trade.SELL,
            shares=50,
            price=Decimal("11.0000"),
            amount=Decimal("550.00"),
        )
        # Set distinct timestamps since auto_now_add may assign the same time
        Trade.objects.filter(pk=t1.pk).update(
            executed_at=now - datetime.timedelta(hours=1)
        )
        Trade.objects.filter(pk=t2.pk).update(executed_at=now)
        trades = list(Trade.objects.all())
        # Most recent first
        assert trades[0].pk == t2.pk
        assert trades[1].pk == t1.pk


# ---------------------------------------------------------------------------
# PerformanceMetric
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPerformanceMetric:
    def test_create_performance_metric(self, performance_metric, portfolio):
        """Create metric, verify fields."""
        pm = PerformanceMetric.objects.get(pk=performance_metric.pk)
        assert pm.portfolio == portfolio
        assert pm.date == datetime.date(2025, 1, 10)
        assert pm.total_value == Decimal("1050000.00")
        assert pm.daily_return == Decimal("0.5000")
        assert pm.cumulative_return == Decimal("5.0000")
        assert pm.max_drawdown == Decimal("2.0000")
        assert pm.sharpe_ratio == Decimal("1.5000")
        assert pm.win_rate == Decimal("60.0000")

    def test_performance_metric_unique_together(self, portfolio):
        """Same portfolio+date is unique."""
        PerformanceMetric.objects.create(
            portfolio=portfolio,
            date=datetime.date(2025, 1, 10),
            total_value=Decimal("1000000.00"),
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PerformanceMetric.objects.create(
                    portfolio=portfolio,
                    date=datetime.date(2025, 1, 10),
                    total_value=Decimal("1100000.00"),
                )


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPortfolioCascadeDelete:
    def test_portfolio_cascade_delete(
        self, portfolio, stock, position, trade, performance_metric
    ):
        """Deleting portfolio cascades to positions, trades, metrics."""
        assert Position.objects.count() == 1
        assert Trade.objects.count() == 1
        assert PerformanceMetric.objects.count() == 1

        portfolio.delete()

        assert Position.objects.count() == 0
        assert Trade.objects.count() == 0
        assert PerformanceMetric.objects.count() == 0
