from django.db import models


class StockBasic(models.Model):
    """A-share stock basic information (股票基本信息)."""

    code = models.CharField("股票代码", max_length=10, primary_key=True)
    name = models.CharField("股票名称", max_length=50)
    industry = models.CharField("行业", max_length=50, blank=True)
    sector = models.CharField("板块", max_length=50, blank=True)
    market = models.CharField("市场", max_length=10)  # SH or SZ
    list_date = models.DateField("上市日期", null=True, blank=True)
    is_active = models.BooleanField("是否活跃", default=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "股票基本信息"
        verbose_name_plural = "股票基本信息"

    def __str__(self):
        return f"{self.code} - {self.name}"


class KlineData(models.Model):
    """Daily K-line / OHLCV data (日K线数据).

    Backed by a TimescaleDB hypertable in production.
    """

    stock = models.ForeignKey(
        StockBasic,
        on_delete=models.CASCADE,
        related_name="klines",
        verbose_name="股票",
    )
    date = models.DateField("交易日期")
    open = models.DecimalField("开盘价", max_digits=12, decimal_places=4)
    high = models.DecimalField("最高价", max_digits=12, decimal_places=4)
    low = models.DecimalField("最低价", max_digits=12, decimal_places=4)
    close = models.DecimalField("收盘价", max_digits=12, decimal_places=4)
    volume = models.BigIntegerField("成交量（手）")
    amount = models.DecimalField("成交额（元）", max_digits=16, decimal_places=4)
    turnover = models.DecimalField(
        "换手率(%)", max_digits=8, decimal_places=4, null=True, blank=True
    )
    change_pct = models.DecimalField(
        "涨跌幅(%)", max_digits=8, decimal_places=4, null=True, blank=True
    )

    class Meta:
        verbose_name = "K线数据"
        verbose_name_plural = "K线数据"
        unique_together = [["stock", "date"]]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.stock_id} {self.date}"


class MoneyFlow(models.Model):
    """Daily capital / money-flow data (资金流向).

    Backed by a TimescaleDB hypertable in production.
    """

    stock = models.ForeignKey(
        StockBasic,
        on_delete=models.CASCADE,
        related_name="money_flows",
        verbose_name="股票",
    )
    date = models.DateField("交易日期")
    main_net = models.DecimalField("主力净流入", max_digits=16, decimal_places=4)
    huge_net = models.DecimalField("超大单净流入", max_digits=16, decimal_places=4)
    big_net = models.DecimalField("大单净流入", max_digits=16, decimal_places=4)
    mid_net = models.DecimalField("中单净流入", max_digits=16, decimal_places=4)
    small_net = models.DecimalField("小单净流入", max_digits=16, decimal_places=4)

    class Meta:
        verbose_name = "资金流向"
        verbose_name_plural = "资金流向"
        unique_together = [["stock", "date"]]

    def __str__(self):
        return f"{self.stock_id} {self.date} 资金流向"


class MarginData(models.Model):
    """Daily margin-trading data (融资融券).

    Backed by a TimescaleDB hypertable in production.
    """

    stock = models.ForeignKey(
        StockBasic,
        on_delete=models.CASCADE,
        related_name="margin_data",
        verbose_name="股票",
    )
    date = models.DateField("交易日期")
    margin_balance = models.DecimalField(
        "融资余额", max_digits=16, decimal_places=4
    )
    short_balance = models.DecimalField(
        "融券余额", max_digits=16, decimal_places=4
    )
    margin_buy = models.DecimalField(
        "融资买入额", max_digits=16, decimal_places=4
    )
    margin_repay = models.DecimalField(
        "融资偿还额", max_digits=16, decimal_places=4
    )

    class Meta:
        verbose_name = "融资融券数据"
        verbose_name_plural = "融资融券数据"
        unique_together = [["stock", "date"]]

    def __str__(self):
        return f"{self.stock_id} {self.date} 融资融券"


class FinancialReport(models.Model):
    """Quarterly / annual financial report data (财务报告)."""

    stock = models.ForeignKey(
        StockBasic,
        on_delete=models.CASCADE,
        related_name="financial_reports",
        verbose_name="股票",
    )
    period = models.CharField("报告期", max_length=10)  # e.g. "2025Q3", "2025A"
    pe_ratio = models.DecimalField(
        "市盈率", max_digits=12, decimal_places=4, null=True, blank=True
    )
    pb_ratio = models.DecimalField(
        "市净率", max_digits=12, decimal_places=4, null=True, blank=True
    )
    roe = models.DecimalField(
        "净资产收益率(%)", max_digits=12, decimal_places=4, null=True, blank=True
    )
    revenue = models.DecimalField(
        "营业收入", max_digits=16, decimal_places=4, null=True, blank=True
    )
    net_profit = models.DecimalField(
        "净利润", max_digits=16, decimal_places=4, null=True, blank=True
    )
    gross_margin = models.DecimalField(
        "毛利率(%)", max_digits=12, decimal_places=4, null=True, blank=True
    )
    debt_ratio = models.DecimalField(
        "资产负债率(%)", max_digits=12, decimal_places=4, null=True, blank=True
    )
    report_date = models.DateField("报告发布日", null=True, blank=True)

    class Meta:
        verbose_name = "财务报告"
        verbose_name_plural = "财务报告"
        unique_together = [["stock", "period"]]

    def __str__(self):
        return f"{self.stock_id} {self.period}"


class NewsArticle(models.Model):
    """Financial news article, optionally linked to a stock (财经新闻)."""

    stock = models.ForeignKey(
        StockBasic,
        on_delete=models.CASCADE,
        related_name="news_articles",
        verbose_name="相关股票",
        null=True,
        blank=True,
    )
    title = models.CharField("标题", max_length=200)
    content = models.TextField("内容", blank=True)
    source = models.CharField("来源", max_length=100, blank=True)
    url = models.URLField("链接", blank=True)
    sentiment_score = models.DecimalField(
        "情感分数", max_digits=5, decimal_places=4, null=True, blank=True
    )
    published_at = models.DateTimeField("发布时间")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "财经新闻"
        verbose_name_plural = "财经新闻"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title
