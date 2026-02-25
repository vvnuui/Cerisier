from abc import ABC, abstractmethod

import pandas as pd


class DataSourceBase(ABC):
    """Abstract base for stock data sources."""

    @abstractmethod
    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch list of all A-share stocks.

        Returns DataFrame with columns: code, name, industry, market
        """

    @abstractmethod
    def fetch_kline(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch daily kline data for a stock.

        Returns DataFrame with columns:
            date, open, high, low, close, volume, amount, turnover, change_pct
        """

    @abstractmethod
    def fetch_money_flow(
        self,
        stock_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch money flow data.

        Returns DataFrame with columns:
            date, main_net, huge_net, big_net, mid_net, small_net
        """

    @abstractmethod
    def fetch_news(
        self, stock_code: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Fetch news articles.

        Returns list of dicts with: title, content, source, url, published_at
        """

    @abstractmethod
    def fetch_financial_report(self, stock_code: str) -> pd.DataFrame:
        """Fetch financial report data.

        Returns DataFrame with columns:
            period, pe_ratio, pb_ratio, roe, revenue, net_profit,
            gross_margin, debt_ratio, report_date
        """

    @abstractmethod
    def fetch_margin_data(
        self,
        stock_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch margin trading data.

        Returns DataFrame with columns:
            date, margin_balance, short_balance, margin_buy, margin_repay
        """
