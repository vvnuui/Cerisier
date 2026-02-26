from django.conf import settings
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
        ordering = ["code"]

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


class Portfolio(models.Model):
    """Paper trading portfolio (模拟交易组合)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
        verbose_name="用户",
    )
    name = models.CharField("组合名称", max_length=100)
    initial_capital = models.DecimalField(
        "初始资金", max_digits=16, decimal_places=2, default=1000000
    )
    cash_balance = models.DecimalField(
        "现金余额", max_digits=16, decimal_places=2, default=1000000
    )
    is_active = models.BooleanField("是否活跃", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "模拟组合"
        verbose_name_plural = "模拟组合"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user})"


class Position(models.Model):
    """Current stock position in a portfolio (持仓)."""

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="组合",
    )
    stock = models.ForeignKey(
        StockBasic,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="股票",
    )
    shares = models.IntegerField("持仓数量", default=0)
    avg_cost = models.DecimalField(
        "平均成本", max_digits=12, decimal_places=4, default=0
    )
    current_price = models.DecimalField(
        "当前价格", max_digits=12, decimal_places=4, default=0
    )
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "持仓"
        verbose_name_plural = "持仓"
        unique_together = [["portfolio", "stock"]]

    def __str__(self):
        return f"{self.portfolio.name} - {self.stock_id} x {self.shares}"

    @property
    def market_value(self):
        """Current market value of position."""
        return self.shares * self.current_price

    @property
    def cost_basis(self):
        """Total cost basis."""
        return self.shares * self.avg_cost

    @property
    def unrealized_pnl(self):
        """Unrealized profit/loss."""
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self):
        """Unrealized P&L percentage."""
        if self.cost_basis == 0:
            return 0
        return float((self.unrealized_pnl / self.cost_basis) * 100)


class Trade(models.Model):
    """Trade execution record (交易记录)."""

    BUY = "BUY"
    SELL = "SELL"
    TRADE_TYPES = [
        (BUY, "买入"),
        (SELL, "卖出"),
    ]

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name="组合",
    )
    stock = models.ForeignKey(
        StockBasic,
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name="股票",
    )
    trade_type = models.CharField(
        "交易类型", max_length=4, choices=TRADE_TYPES
    )
    shares = models.IntegerField("交易数量")
    price = models.DecimalField("成交价格", max_digits=12, decimal_places=4)
    amount = models.DecimalField("成交金额", max_digits=16, decimal_places=2)
    commission = models.DecimalField(
        "手续费", max_digits=10, decimal_places=2, default=0
    )
    reason = models.CharField("交易理由", max_length=200, blank=True)
    executed_at = models.DateTimeField("执行时间", auto_now_add=True)

    class Meta:
        verbose_name = "交易记录"
        verbose_name_plural = "交易记录"
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.trade_type} {self.stock_id} x {self.shares} @ {self.price}"


class PerformanceMetric(models.Model):
    """Daily performance metrics for a portfolio (绩效指标)."""

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="performance_metrics",
        verbose_name="组合",
    )
    date = models.DateField("日期")
    total_value = models.DecimalField(
        "总资产", max_digits=16, decimal_places=2
    )
    daily_return = models.DecimalField(
        "日收益率(%)", max_digits=8, decimal_places=4, default=0
    )
    cumulative_return = models.DecimalField(
        "累计收益率(%)", max_digits=10, decimal_places=4, default=0
    )
    max_drawdown = models.DecimalField(
        "最大回撤(%)", max_digits=8, decimal_places=4, default=0
    )
    sharpe_ratio = models.DecimalField(
        "夏普比率", max_digits=8, decimal_places=4, null=True, blank=True
    )
    win_rate = models.DecimalField(
        "胜率(%)", max_digits=8, decimal_places=4, null=True, blank=True
    )

    class Meta:
        verbose_name = "绩效指标"
        verbose_name_plural = "绩效指标"
        unique_together = [["portfolio", "date"]]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.portfolio.name} {self.date} 绩效"
