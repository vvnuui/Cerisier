import logging

import pandas as pd
from decouple import config
from django.conf import settings

from .base import DataSourceBase
from .akshare_source import AKShareSource
from .tushare_source import TushareSource

logger = logging.getLogger(__name__)


class DataSourceRouter:
    """Routes data requests to available sources with automatic failover.

    Sources are tried in order; the first source that returns a non-empty
    result wins.  If every source fails an empty DataFrame (or list) is
    returned so callers never need to handle ``None``.
    """

    def __init__(self, sources: list[DataSourceBase] | None = None):
        if sources is None:
            sources = self._default_sources()
        self.sources = sources

    @staticmethod
    def _default_sources() -> list[DataSourceBase]:
        sources: list[DataSourceBase] = [AKShareSource()]
        # Add Tushare if a token is configured
        token = getattr(settings, "TUSHARE_TOKEN", "") or config(
            "TUSHARE_TOKEN", default=""
        )
        if token:
            sources.append(TushareSource(token=token))
        return sources

    # ------------------------------------------------------------------
    # public API  -- one method per DataSourceBase method
    # ------------------------------------------------------------------

    def fetch_stock_list(self) -> pd.DataFrame:
        """Try each source in order; return the first successful result."""
        for source in self.sources:
            try:
                result = source.fetch_stock_list()
                if result is not None and not result.empty:
                    return result
            except Exception as exc:
                logger.warning(
                    "Source %s.fetch_stock_list failed: %s",
                    source.__class__.__name__,
                    exc,
                )
                continue
        return pd.DataFrame(columns=["code", "name", "industry", "market"])

    def fetch_kline(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        for source in self.sources:
            try:
                result = source.fetch_kline(stock_code, start_date, end_date)
                if result is not None and not result.empty:
                    return result
            except Exception as exc:
                logger.warning(
                    "Source %s.fetch_kline failed: %s",
                    source.__class__.__name__,
                    exc,
                )
                continue
        return pd.DataFrame(
            columns=[
                "date", "open", "high", "low", "close",
                "volume", "amount", "turnover", "change_pct",
            ]
        )

    def fetch_money_flow(
        self,
        stock_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        for source in self.sources:
            try:
                result = source.fetch_money_flow(
                    stock_code, start_date, end_date
                )
                if result is not None and not result.empty:
                    return result
            except Exception as exc:
                logger.warning(
                    "Source %s.fetch_money_flow failed: %s",
                    source.__class__.__name__,
                    exc,
                )
                continue
        return pd.DataFrame(
            columns=[
                "date", "main_net", "huge_net", "big_net",
                "mid_net", "small_net",
            ]
        )

    def fetch_news(
        self, stock_code: str | None = None, limit: int = 50
    ) -> list[dict]:
        for source in self.sources:
            try:
                result = source.fetch_news(stock_code, limit)
                if result:
                    return result
            except Exception as exc:
                logger.warning(
                    "Source %s.fetch_news failed: %s",
                    source.__class__.__name__,
                    exc,
                )
                continue
        return []

    def fetch_financial_report(self, stock_code: str) -> pd.DataFrame:
        for source in self.sources:
            try:
                result = source.fetch_financial_report(stock_code)
                if result is not None and not result.empty:
                    return result
            except Exception as exc:
                logger.warning(
                    "Source %s.fetch_financial_report failed: %s",
                    source.__class__.__name__,
                    exc,
                )
                continue
        return pd.DataFrame(
            columns=[
                "period", "pe_ratio", "pb_ratio", "roe", "revenue",
                "net_profit", "gross_margin", "debt_ratio", "report_date",
            ]
        )

    def fetch_margin_data(
        self,
        stock_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        for source in self.sources:
            try:
                result = source.fetch_margin_data(
                    stock_code, start_date, end_date
                )
                if result is not None and not result.empty:
                    return result
            except Exception as exc:
                logger.warning(
                    "Source %s.fetch_margin_data failed: %s",
                    source.__class__.__name__,
                    exc,
                )
                continue
        return pd.DataFrame(
            columns=[
                "date", "margin_balance", "short_balance",
                "margin_buy", "margin_repay",
            ]
        )
