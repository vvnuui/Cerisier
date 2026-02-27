"""Tests for the paper trading simulator API endpoints."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.quant.models import PerformanceMetric, Portfolio, Position, StockBasic, Trade

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
def other_user(db):
    return User.objects.create_user(
        username="other", email="other@e.com", password="pass456"
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauth_client():
    return APIClient()


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
def other_portfolio(other_user):
    return Portfolio.objects.create(
        user=other_user,
        name="Other Portfolio",
        initial_capital=Decimal("500000"),
        cash_balance=Decimal("500000"),
    )


# ---------------------------------------------------------------------------
# Portfolio CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPortfolioCRUD:
    def test_create_portfolio(self, api_client):
        """POST /api/quant/portfolios/ creates a portfolio and returns 201."""
        data = {"name": "My Portfolio", "initial_capital": "500000.00"}
        resp = api_client.post("/api/quant/portfolios/", data)

        assert resp.status_code == http_status.HTTP_201_CREATED
        assert Portfolio.objects.filter(name="My Portfolio").exists()

        portfolio = Portfolio.objects.get(name="My Portfolio")
        assert portfolio.cash_balance == Decimal("500000.00")
        assert portfolio.initial_capital == Decimal("500000.00")

    def test_list_portfolios(self, api_client, portfolio, other_portfolio):
        """GET /api/quant/portfolios/ returns only the authenticated user's portfolios."""
        resp = api_client.get("/api/quant/portfolios/")

        assert resp.status_code == http_status.HTTP_200_OK
        results = resp.data["results"]
        assert len(results) == 1
        assert results[0]["name"] == "Test Portfolio"

    def test_retrieve_portfolio_summary(self, api_client, portfolio, stock):
        """GET /api/quant/portfolios/{id}/ returns engine summary with positions."""
        # Buy some stock first to have a position
        from apps.quant.simulator.engine import SimulatorEngine

        engine = SimulatorEngine(portfolio)
        engine.buy(stock.code, 100, Decimal("10.00"))

        resp = api_client.get(f"/api/quant/portfolios/{portfolio.pk}/")

        assert resp.status_code == http_status.HTTP_200_OK
        assert "portfolio_id" in resp.data
        assert "cash_balance" in resp.data
        assert "total_market_value" in resp.data
        assert "total_value" in resp.data
        assert "positions" in resp.data
        assert resp.data["position_count"] == 1
        assert resp.data["positions"][0]["stock_code"] == "000001"

    def test_delete_portfolio(self, api_client, portfolio):
        """DELETE /api/quant/portfolios/{id}/ deletes and returns 204."""
        resp = api_client.delete(f"/api/quant/portfolios/{portfolio.pk}/")

        assert resp.status_code == http_status.HTTP_204_NO_CONTENT
        assert not Portfolio.objects.filter(pk=portfolio.pk).exists()

    def test_update_portfolio(self, api_client, portfolio):
        """PUT /api/quant/portfolios/{id}/ updates portfolio fields."""
        data = {
            "name": "Updated Name",
            "initial_capital": "1000000.00",
            "is_active": False,
        }
        resp = api_client.put(f"/api/quant/portfolios/{portfolio.pk}/", data)

        assert resp.status_code == http_status.HTTP_200_OK
        portfolio.refresh_from_db()
        assert portfolio.name == "Updated Name"
        assert portfolio.is_active is False


# ---------------------------------------------------------------------------
# Trade execution tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTradeExecution:
    def test_execute_buy_trade(self, api_client, portfolio, stock):
        """POST /api/quant/portfolios/{id}/trade/ with BUY returns 201."""
        data = {
            "stock_code": stock.code,
            "trade_type": "BUY",
            "shares": 100,
            "price": "10.0000",
            "reason": "test buy",
        }
        resp = api_client.post(
            f"/api/quant/portfolios/{portfolio.pk}/trade/", data
        )

        assert resp.status_code == http_status.HTTP_201_CREATED
        assert resp.data["stock_code"] == "000001"
        assert resp.data["trade_type"] == "BUY"
        assert resp.data["shares"] == 100
        assert Trade.objects.filter(portfolio=portfolio).count() == 1

    def test_execute_sell_trade(self, api_client, portfolio, stock):
        """Buy then sell via API, verify sell returns 201."""
        # First buy via API
        buy_data = {
            "stock_code": stock.code,
            "trade_type": "BUY",
            "shares": 100,
            "price": "10.0000",
        }
        api_client.post(f"/api/quant/portfolios/{portfolio.pk}/trade/", buy_data)

        # Now sell
        sell_data = {
            "stock_code": stock.code,
            "trade_type": "SELL",
            "shares": 100,
            "price": "12.0000",
            "reason": "take profit",
        }
        resp = api_client.post(
            f"/api/quant/portfolios/{portfolio.pk}/trade/", sell_data
        )

        assert resp.status_code == http_status.HTTP_201_CREATED
        assert resp.data["trade_type"] == "SELL"
        assert resp.data["shares"] == 100
        assert Trade.objects.filter(portfolio=portfolio).count() == 2

    def test_trade_insufficient_funds(self, api_client, portfolio, stock):
        """Buy with too much money returns 400."""
        data = {
            "stock_code": stock.code,
            "trade_type": "BUY",
            "shares": 1000000,
            "price": "1100.0000",
        }
        resp = api_client.post(
            f"/api/quant/portfolios/{portfolio.pk}/trade/", data
        )

        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "error" in resp.data

    def test_trade_insufficient_shares(self, api_client, portfolio, stock):
        """Sell without position returns 400."""
        data = {
            "stock_code": stock.code,
            "trade_type": "SELL",
            "shares": 100,
            "price": "10.0000",
        }
        resp = api_client.post(
            f"/api/quant/portfolios/{portfolio.pk}/trade/", data
        )

        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "error" in resp.data

    def test_trade_invalid_data(self, api_client, portfolio):
        """Missing required fields returns 400."""
        # Missing stock_code, trade_type, shares, price
        data = {"reason": "no other fields"}
        resp = api_client.post(
            f"/api/quant/portfolios/{portfolio.pk}/trade/", data
        )

        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_trade_invalid_shares_zero(self, api_client, portfolio, stock):
        """Shares = 0 returns 400 (min_value=1 in serializer)."""
        data = {
            "stock_code": stock.code,
            "trade_type": "BUY",
            "shares": 0,
            "price": "10.0000",
        }
        resp = api_client.post(
            f"/api/quant/portfolios/{portfolio.pk}/trade/", data
        )

        assert resp.status_code == http_status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Nested endpoints tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNestedEndpoints:
    def test_list_positions(self, api_client, portfolio, stock):
        """GET /api/quant/portfolios/{id}/positions/ lists positions."""
        from apps.quant.simulator.engine import SimulatorEngine

        engine = SimulatorEngine(portfolio)
        engine.buy(stock.code, 100, Decimal("10.00"))

        resp = api_client.get(f"/api/quant/portfolios/{portfolio.pk}/positions/")

        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["stock_code"] == "000001"
        assert resp.data[0]["stock_name"] == "平安银行"
        assert resp.data[0]["shares"] == 100
        # market_value should be a float
        assert isinstance(resp.data[0]["market_value"], float)

    def test_list_positions_empty(self, api_client, portfolio):
        """Positions endpoint returns empty list when no positions."""
        resp = api_client.get(f"/api/quant/portfolios/{portfolio.pk}/positions/")

        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data == []

    def test_list_trades(self, api_client, portfolio, stock):
        """GET /api/quant/portfolios/{id}/trades/ lists trade history."""
        from apps.quant.simulator.engine import SimulatorEngine

        engine = SimulatorEngine(portfolio)
        engine.buy(stock.code, 100, Decimal("10.00"), reason="api test")

        resp = api_client.get(f"/api/quant/portfolios/{portfolio.pk}/trades/")

        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["stock_code"] == "000001"
        assert resp.data[0]["trade_type"] == "BUY"
        assert resp.data[0]["reason"] == "api test"

    def test_list_performance(self, api_client, portfolio):
        """GET /api/quant/portfolios/{id}/performance/ lists metrics."""
        # Create a metric manually
        from datetime import date

        PerformanceMetric.objects.create(
            portfolio=portfolio,
            date=date(2025, 1, 1),
            total_value=Decimal("1000000.00"),
            daily_return=Decimal("0.0"),
            cumulative_return=Decimal("0.0"),
            max_drawdown=Decimal("0.0"),
        )

        resp = api_client.get(
            f"/api/quant/portfolios/{portfolio.pk}/performance/"
        )

        assert resp.status_code == http_status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["date"] == "2025-01-01"

    def test_calculate_performance(self, api_client, portfolio):
        """POST /api/quant/portfolios/{id}/calculate-performance/ creates metric."""
        resp = api_client.post(
            f"/api/quant/portfolios/{portfolio.pk}/calculate-performance/"
        )

        assert resp.status_code == http_status.HTTP_200_OK
        assert "total_value" in resp.data
        assert "daily_return" in resp.data
        assert "cumulative_return" in resp.data
        assert PerformanceMetric.objects.filter(portfolio=portfolio).count() == 1


# ---------------------------------------------------------------------------
# Auth and multi-tenant tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuthAndMultiTenant:
    def test_unauthenticated_access(self, unauth_client):
        """Unauthenticated request returns 401."""
        resp = unauth_client.get("/api/quant/portfolios/")

        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_create(self, unauth_client):
        """Unauthenticated POST returns 401."""
        data = {"name": "Hacker Portfolio", "initial_capital": "100000.00"}
        resp = unauth_client.post("/api/quant/portfolios/", data)

        assert resp.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_other_user_portfolio_not_visible(
        self, api_client, other_portfolio
    ):
        """Cannot access another user's portfolio, returns 404."""
        resp = api_client.get(
            f"/api/quant/portfolios/{other_portfolio.pk}/"
        )

        assert resp.status_code == http_status.HTTP_404_NOT_FOUND

    def test_other_user_portfolio_trade(self, api_client, other_portfolio, stock):
        """Cannot execute trade on another user's portfolio, returns 404."""
        data = {
            "stock_code": stock.code,
            "trade_type": "BUY",
            "shares": 100,
            "price": "10.0000",
        }
        resp = api_client.post(
            f"/api/quant/portfolios/{other_portfolio.pk}/trade/", data
        )

        assert resp.status_code == http_status.HTTP_404_NOT_FOUND

    def test_other_user_portfolio_delete(self, api_client, other_portfolio):
        """Cannot delete another user's portfolio, returns 404."""
        resp = api_client.delete(
            f"/api/quant/portfolios/{other_portfolio.pk}/"
        )

        assert resp.status_code == http_status.HTTP_404_NOT_FOUND
        assert Portfolio.objects.filter(pk=other_portfolio.pk).exists()
