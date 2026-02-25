"""Tests for the quant Celery tasks.

All external data-source calls are mocked via ``DataSourceRouter`` so that
tests run without network access, third-party API tokens, or a Celery broker.
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from django.utils import timezone

from apps.quant.models import (
    FinancialReport,
    KlineData,
    MarginData,
    MoneyFlow,
    NewsArticle,
    StockBasic,
)
from apps.quant.tasks import (
    sync_daily_kline,
    sync_financial_reports,
    sync_margin_data,
    sync_money_flow,
    sync_news,
    sync_stock_list,
    validate_data,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

ROUTER_PATH = "apps.quant.tasks.DataSourceRouter"


@pytest.fixture
def stock():
    return StockBasic.objects.create(
        code="000001",
        name="平安银行",
        industry="银行",
        sector="金融",
        market="SZ",
        list_date=datetime.date(1991, 4, 3),
        is_active=True,
    )


@pytest.fixture
def another_stock():
    return StockBasic.objects.create(
        code="600519",
        name="贵州茅台",
        industry="白酒",
        sector="消费",
        market="SH",
        list_date=datetime.date(2001, 8, 27),
        is_active=True,
    )


# ---------------------------------------------------------------------------
# sync_stock_list
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncStockList:
    def test_sync_stock_list_creates_stocks(self):
        """Stocks are created when the data source returns a non-empty DF."""
        mock_df = pd.DataFrame(
            [
                {"code": "000001", "name": "平安银行", "industry": "银行", "market": "SZ"},
                {"code": "600519", "name": "贵州茅台", "industry": "白酒", "market": "SH"},
            ]
        )

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_stock_list.return_value = mock_df
            result = sync_stock_list()

        assert result["created"] == 2
        assert result["updated"] == 0
        assert StockBasic.objects.count() == 2
        assert StockBasic.objects.get(code="000001").name == "平安银行"
        assert StockBasic.objects.get(code="600519").name == "贵州茅台"

    def test_sync_stock_list_updates_existing(self, stock):
        """Existing stocks are updated (not duplicated) on subsequent syncs."""
        mock_df = pd.DataFrame(
            [
                {"code": "000001", "name": "平安银行NEW", "industry": "银行业", "market": "SZ"},
            ]
        )

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_stock_list.return_value = mock_df
            result = sync_stock_list()

        assert result["created"] == 0
        assert result["updated"] == 1
        assert StockBasic.objects.count() == 1
        refreshed = StockBasic.objects.get(code="000001")
        assert refreshed.name == "平安银行NEW"
        assert refreshed.industry == "银行业"

    def test_sync_stock_list_empty_response(self):
        """An empty DataFrame from the source returns synced=0."""
        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_stock_list.return_value = pd.DataFrame()
            result = sync_stock_list()

        assert result == {"synced": 0}
        assert StockBasic.objects.count() == 0


# ---------------------------------------------------------------------------
# sync_daily_kline
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncDailyKline:
    def test_sync_daily_kline_single_stock(self, stock):
        """Kline records are created for a specific stock_code."""
        mock_df = pd.DataFrame(
            [
                {
                    "date": "2025-01-10",
                    "open": 10.50,
                    "high": 11.00,
                    "low": 10.20,
                    "close": 10.80,
                    "volume": 1000000,
                    "amount": 10800000.0,
                    "turnover": 1.50,
                    "change_pct": 2.86,
                },
                {
                    "date": "2025-01-11",
                    "open": 10.80,
                    "high": 11.20,
                    "low": 10.50,
                    "close": 11.00,
                    "volume": 1200000,
                    "amount": 13200000.0,
                    "turnover": 1.80,
                    "change_pct": 1.85,
                },
            ]
        )

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_kline.return_value = mock_df
            result = sync_daily_kline(stock_code="000001")

        assert result["synced"] == 2
        assert result["errors"] == 0
        assert KlineData.objects.count() == 2
        k = KlineData.objects.get(stock_id="000001", date="2025-01-10")
        assert k.open == Decimal("10.5")
        assert k.close == Decimal("10.8")
        assert k.volume == 1000000

    def test_sync_daily_kline_all_stocks(self, stock, another_stock):
        """When no stock_code is given, all active stocks are synced."""
        mock_df = pd.DataFrame(
            [
                {
                    "date": "2025-01-10",
                    "open": 10.50,
                    "high": 11.00,
                    "low": 10.20,
                    "close": 10.80,
                    "volume": 1000000,
                    "amount": 10800000.0,
                    "turnover": 1.50,
                    "change_pct": 2.86,
                },
            ]
        )

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_kline.return_value = mock_df
            result = sync_daily_kline()

        assert result["synced"] == 2  # 1 row per stock * 2 stocks
        assert result["errors"] == 0
        assert KlineData.objects.count() == 2

    def test_sync_daily_kline_handles_error(self, stock, another_stock):
        """If one stock fails, the task continues with the remaining stocks."""
        mock_df = pd.DataFrame(
            [
                {
                    "date": "2025-01-10",
                    "open": 10.50,
                    "high": 11.00,
                    "low": 10.20,
                    "close": 10.80,
                    "volume": 1000000,
                    "amount": 10800000.0,
                    "turnover": 1.50,
                    "change_pct": 2.86,
                },
            ]
        )

        call_count = 0

        def side_effect(code, start, end):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated API error")
            return mock_df

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_kline.side_effect = side_effect
            result = sync_daily_kline()

        assert result["errors"] == 1
        # One stock succeeded, one failed
        assert result["synced"] == 1
        assert KlineData.objects.count() == 1


# ---------------------------------------------------------------------------
# sync_money_flow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncMoneyFlow:
    def test_sync_money_flow(self, stock):
        """Money-flow records are created correctly."""
        mock_df = pd.DataFrame(
            [
                {
                    "date": "2025-01-10",
                    "main_net": 5000000.0,
                    "huge_net": 3000000.0,
                    "big_net": 2000000.0,
                    "mid_net": -500000.0,
                    "small_net": -1500000.0,
                },
            ]
        )

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_money_flow.return_value = mock_df
            result = sync_money_flow(stock_code="000001")

        assert result["synced"] == 1
        assert result["errors"] == 0
        assert MoneyFlow.objects.count() == 1
        mf = MoneyFlow.objects.get(stock_id="000001", date="2025-01-10")
        assert mf.main_net == Decimal("5000000.0")
        assert mf.small_net == Decimal("-1500000.0")


# ---------------------------------------------------------------------------
# sync_margin_data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncMarginData:
    def test_sync_margin_data(self, stock):
        """Margin-data records are created correctly."""
        mock_df = pd.DataFrame(
            [
                {
                    "date": "2025-01-10",
                    "margin_balance": 1000000000.0,
                    "short_balance": 50000000.0,
                    "margin_buy": 200000000.0,
                    "margin_repay": 180000000.0,
                },
            ]
        )

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_margin_data.return_value = mock_df
            result = sync_margin_data(stock_code="000001")

        assert result["synced"] == 1
        assert result["errors"] == 0
        assert MarginData.objects.count() == 1
        md = MarginData.objects.get(stock_id="000001", date="2025-01-10")
        assert md.margin_balance == Decimal("1000000000.0")
        assert md.margin_repay == Decimal("180000000.0")


# ---------------------------------------------------------------------------
# sync_financial_reports
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncFinancialReports:
    def test_sync_financial_reports(self, stock):
        """Financial-report records are created correctly."""
        mock_df = pd.DataFrame(
            [
                {
                    "period": "2025Q3",
                    "pe_ratio": 8.50,
                    "pb_ratio": 0.90,
                    "roe": 12.50,
                    "revenue": 1500000000.0,
                    "net_profit": 300000000.0,
                    "gross_margin": 35.0,
                    "debt_ratio": 92.0,
                    "report_date": "2025-10-28",
                },
            ]
        )

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_financial_report.return_value = mock_df
            result = sync_financial_reports(stock_code="000001")

        assert result["synced"] == 1
        assert result["errors"] == 0
        assert FinancialReport.objects.count() == 1
        fr = FinancialReport.objects.get(stock_id="000001", period="2025Q3")
        assert fr.pe_ratio == Decimal("8.5")
        assert fr.roe == Decimal("12.5")
        assert fr.revenue == Decimal("1500000000.0")
        assert fr.report_date == datetime.date(2025, 10, 28)


# ---------------------------------------------------------------------------
# sync_news
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncNews:
    def test_sync_news_creates_articles(self, stock):
        """News articles are created from the data-source response."""
        pub_time = timezone.now().isoformat()
        mock_articles = [
            {
                "title": "平安银行发布年报",
                "content": "平安银行2025年业绩亮眼...",
                "source": "新浪财经",
                "url": "https://example.com/1",
                "published_at": pub_time,
            },
            {
                "title": "银行板块走强",
                "content": "多家银行股涨停...",
                "source": "东方财富",
                "url": "https://example.com/2",
                "published_at": pub_time,
            },
        ]

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_news.return_value = mock_articles
            result = sync_news(stock_code="000001")

        assert result["created"] == 2
        assert result["total_fetched"] == 2
        assert NewsArticle.objects.count() == 2
        assert NewsArticle.objects.filter(title="平安银行发布年报").exists()

    def test_sync_news_deduplicates(self, stock):
        """Calling sync_news twice with the same data does not create duplicates."""
        pub_time = timezone.now().isoformat()
        mock_articles = [
            {
                "title": "平安银行发布年报",
                "content": "平安银行2025年业绩亮眼...",
                "source": "新浪财经",
                "url": "https://example.com/1",
                "published_at": pub_time,
            },
        ]

        with patch(ROUTER_PATH) as MockRouter:
            MockRouter.return_value.fetch_news.return_value = mock_articles
            result1 = sync_news(stock_code="000001")
            result2 = sync_news(stock_code="000001")

        assert result1["created"] == 1
        assert result2["created"] == 0
        assert NewsArticle.objects.count() == 1


# ---------------------------------------------------------------------------
# validate_data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidateData:
    def test_validate_data_no_issues(self, stock):
        """No issues when recent kline data exists for all active stocks."""
        KlineData.objects.create(
            stock=stock,
            date=datetime.date.today() - datetime.timedelta(days=1),
            open=Decimal("10.5000"),
            high=Decimal("11.0000"),
            low=Decimal("10.2000"),
            close=Decimal("10.8000"),
            volume=1000000,
            amount=Decimal("10800000.0000"),
        )

        result = validate_data()

        assert result["issues"] == []
        assert result["active_stocks"] == 1
        assert result["stocks_with_recent_data"] == 1

    def test_validate_data_detects_gaps(self, stock, another_stock):
        """Gaps are detected when most active stocks have no recent kline data."""
        # Both stocks are active but neither has recent kline data.
        result = validate_data()

        assert result["active_stocks"] == 2
        assert result["stocks_with_recent_data"] == 0
        assert len(result["issues"]) >= 1
        assert "0/2" in result["issues"][0]
