import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.quant.models import (
    FinancialReport,
    KlineData,
    MarginData,
    MoneyFlow,
    NewsArticle,
    StockBasic,
)


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


@pytest.fixture
def kline(stock):
    return KlineData.objects.create(
        stock=stock,
        date=datetime.date(2025, 1, 10),
        open=Decimal("10.5000"),
        high=Decimal("11.0000"),
        low=Decimal("10.2000"),
        close=Decimal("10.8000"),
        volume=1000000,
        amount=Decimal("10800000.0000"),
        turnover=Decimal("1.5000"),
        change_pct=Decimal("2.8600"),
    )


# ---------------------------------------------------------------------------
# StockBasic
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStockBasic:
    def test_create_stock_basic(self, stock):
        """Create a stock and verify all fields are persisted correctly."""
        s = StockBasic.objects.get(code="000001")
        assert s.name == "平安银行"
        assert s.industry == "银行"
        assert s.sector == "金融"
        assert s.market == "SZ"
        assert s.list_date == datetime.date(1991, 4, 3)
        assert s.is_active is True
        assert s.updated_at is not None

    def test_stock_basic_str(self, stock):
        """__str__ returns 'code - name'."""
        assert str(stock) == "000001 - 平安银行"

    def test_stock_basic_primary_key(self, stock):
        """The `code` field is the primary key."""
        assert stock.pk == "000001"
        assert StockBasic._meta.pk.name == "code"


# ---------------------------------------------------------------------------
# KlineData
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestKlineData:
    def test_create_kline_data(self, stock, kline):
        """Create a kline record and verify fields."""
        k = KlineData.objects.get(stock=stock, date=datetime.date(2025, 1, 10))
        assert k.open == Decimal("10.5000")
        assert k.high == Decimal("11.0000")
        assert k.low == Decimal("10.2000")
        assert k.close == Decimal("10.8000")
        assert k.volume == 1000000
        assert k.amount == Decimal("10800000.0000")
        assert k.turnover == Decimal("1.5000")
        assert k.change_pct == Decimal("2.8600")

    def test_kline_unique_together(self, stock, kline):
        """Same stock + date must raise IntegrityError."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                KlineData.objects.create(
                    stock=stock,
                    date=datetime.date(2025, 1, 10),
                    open=Decimal("10.0000"),
                    high=Decimal("10.0000"),
                    low=Decimal("10.0000"),
                    close=Decimal("10.0000"),
                    volume=0,
                    amount=Decimal("0.0000"),
                )

    def test_kline_ordering(self, stock):
        """Default ordering is -date (most recent first)."""
        KlineData.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 8),
            open=Decimal("10.0000"),
            high=Decimal("10.0000"),
            low=Decimal("10.0000"),
            close=Decimal("10.0000"),
            volume=100,
            amount=Decimal("1000.0000"),
        )
        KlineData.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 10),
            open=Decimal("11.0000"),
            high=Decimal("11.0000"),
            low=Decimal("11.0000"),
            close=Decimal("11.0000"),
            volume=200,
            amount=Decimal("2200.0000"),
        )
        KlineData.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 9),
            open=Decimal("10.5000"),
            high=Decimal("10.5000"),
            low=Decimal("10.5000"),
            close=Decimal("10.5000"),
            volume=150,
            amount=Decimal("1575.0000"),
        )
        dates = list(KlineData.objects.values_list("date", flat=True))
        assert dates == [
            datetime.date(2025, 1, 10),
            datetime.date(2025, 1, 9),
            datetime.date(2025, 1, 8),
        ]


# ---------------------------------------------------------------------------
# MoneyFlow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMoneyFlow:
    def test_create_money_flow(self, stock):
        """Create a money-flow record and verify fields."""
        mf = MoneyFlow.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 10),
            main_net=Decimal("5000000.0000"),
            huge_net=Decimal("3000000.0000"),
            big_net=Decimal("2000000.0000"),
            mid_net=Decimal("-500000.0000"),
            small_net=Decimal("-1500000.0000"),
        )
        fetched = MoneyFlow.objects.get(pk=mf.pk)
        assert fetched.main_net == Decimal("5000000.0000")
        assert fetched.huge_net == Decimal("3000000.0000")
        assert fetched.big_net == Decimal("2000000.0000")
        assert fetched.mid_net == Decimal("-500000.0000")
        assert fetched.small_net == Decimal("-1500000.0000")

    def test_money_flow_unique_together(self, stock):
        """Same stock + date must raise IntegrityError."""
        MoneyFlow.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 10),
            main_net=Decimal("5000000.0000"),
            huge_net=Decimal("3000000.0000"),
            big_net=Decimal("2000000.0000"),
            mid_net=Decimal("-500000.0000"),
            small_net=Decimal("-1500000.0000"),
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                MoneyFlow.objects.create(
                    stock=stock,
                    date=datetime.date(2025, 1, 10),
                    main_net=Decimal("0.0000"),
                    huge_net=Decimal("0.0000"),
                    big_net=Decimal("0.0000"),
                    mid_net=Decimal("0.0000"),
                    small_net=Decimal("0.0000"),
                )


# ---------------------------------------------------------------------------
# MarginData
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMarginData:
    def test_create_margin_data(self, stock):
        """Create a margin-data record and verify fields."""
        md = MarginData.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 10),
            margin_balance=Decimal("1000000000.0000"),
            short_balance=Decimal("50000000.0000"),
            margin_buy=Decimal("200000000.0000"),
            margin_repay=Decimal("180000000.0000"),
        )
        fetched = MarginData.objects.get(pk=md.pk)
        assert fetched.margin_balance == Decimal("1000000000.0000")
        assert fetched.short_balance == Decimal("50000000.0000")
        assert fetched.margin_buy == Decimal("200000000.0000")
        assert fetched.margin_repay == Decimal("180000000.0000")


# ---------------------------------------------------------------------------
# FinancialReport
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFinancialReport:
    def test_create_financial_report(self, stock):
        """Create a financial report linked to a stock."""
        fr = FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
            pe_ratio=Decimal("8.5000"),
            pb_ratio=Decimal("0.9000"),
            roe=Decimal("12.5000"),
            revenue=Decimal("1500000000.0000"),
            net_profit=Decimal("300000000.0000"),
            gross_margin=Decimal("35.0000"),
            debt_ratio=Decimal("92.0000"),
            report_date=datetime.date(2025, 10, 28),
        )
        fetched = FinancialReport.objects.get(pk=fr.pk)
        assert fetched.period == "2025Q3"
        assert fetched.pe_ratio == Decimal("8.5000")
        assert fetched.pb_ratio == Decimal("0.9000")
        assert fetched.roe == Decimal("12.5000")
        assert fetched.revenue == Decimal("1500000000.0000")
        assert fetched.net_profit == Decimal("300000000.0000")
        assert fetched.gross_margin == Decimal("35.0000")
        assert fetched.debt_ratio == Decimal("92.0000")
        assert fetched.report_date == datetime.date(2025, 10, 28)

    def test_financial_report_unique_together(self, stock):
        """Same stock + period must raise IntegrityError."""
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                FinancialReport.objects.create(
                    stock=stock,
                    period="2025Q3",
                )


# ---------------------------------------------------------------------------
# NewsArticle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNewsArticle:
    def test_create_news_article(self, stock):
        """Create a news article linked to a stock."""
        pub_time = timezone.now()
        na = NewsArticle.objects.create(
            stock=stock,
            title="平安银行2025年三季报发布",
            content="平安银行公布了2025年三季度业绩...",
            source="新浪财经",
            url="https://finance.sina.com.cn/article/123",
            sentiment_score=Decimal("0.6500"),
            published_at=pub_time,
        )
        fetched = NewsArticle.objects.get(pk=na.pk)
        assert fetched.title == "平安银行2025年三季报发布"
        assert fetched.content == "平安银行公布了2025年三季度业绩..."
        assert fetched.source == "新浪财经"
        assert fetched.url == "https://finance.sina.com.cn/article/123"
        assert fetched.sentiment_score == Decimal("0.6500")
        assert fetched.created_at is not None

    def test_news_article_ordering(self, stock):
        """Default ordering is -published_at (most recent first)."""
        t1 = timezone.now() - datetime.timedelta(hours=2)
        t2 = timezone.now() - datetime.timedelta(hours=1)
        t3 = timezone.now()
        NewsArticle.objects.create(stock=stock, title="Old", published_at=t1)
        NewsArticle.objects.create(stock=stock, title="Recent", published_at=t3)
        NewsArticle.objects.create(stock=stock, title="Mid", published_at=t2)
        titles = list(NewsArticle.objects.values_list("title", flat=True))
        assert titles == ["Recent", "Mid", "Old"]

    def test_news_article_nullable_stock(self):
        """Market-wide news can be created without a stock reference."""
        na = NewsArticle.objects.create(
            stock=None,
            title="央行宣布降准50个基点",
            published_at=timezone.now(),
        )
        assert na.stock is None
        assert na.pk is not None


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCascadeDelete:
    def test_stock_cascade_delete(self, stock):
        """Deleting a stock cascades to all related records."""
        KlineData.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 10),
            open=Decimal("10.0000"),
            high=Decimal("11.0000"),
            low=Decimal("10.0000"),
            close=Decimal("10.5000"),
            volume=100000,
            amount=Decimal("1050000.0000"),
        )
        MoneyFlow.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 10),
            main_net=Decimal("5000000.0000"),
            huge_net=Decimal("3000000.0000"),
            big_net=Decimal("2000000.0000"),
            mid_net=Decimal("-500000.0000"),
            small_net=Decimal("-1500000.0000"),
        )
        MarginData.objects.create(
            stock=stock,
            date=datetime.date(2025, 1, 10),
            margin_balance=Decimal("1000000000.0000"),
            short_balance=Decimal("50000000.0000"),
            margin_buy=Decimal("200000000.0000"),
            margin_repay=Decimal("180000000.0000"),
        )
        FinancialReport.objects.create(
            stock=stock,
            period="2025Q3",
        )
        NewsArticle.objects.create(
            stock=stock,
            title="Test news",
            published_at=timezone.now(),
        )

        assert KlineData.objects.count() == 1
        assert MoneyFlow.objects.count() == 1
        assert MarginData.objects.count() == 1
        assert FinancialReport.objects.count() == 1
        assert NewsArticle.objects.count() == 1

        stock.delete()

        assert KlineData.objects.count() == 0
        assert MoneyFlow.objects.count() == 0
        assert MarginData.objects.count() == 0
        assert FinancialReport.objects.count() == 0
        assert NewsArticle.objects.count() == 0
