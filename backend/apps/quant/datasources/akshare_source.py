import logging

import akshare as ak
import pandas as pd

from .base import DataSourceBase

logger = logging.getLogger(__name__)


class AKShareSource(DataSourceBase):
    """Primary data source using AKShare for Chinese A-share market data."""

    # ------------------------------------------------------------------
    # stock list
    # ------------------------------------------------------------------

    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch list of all A-share stocks.

        Uses ``ak.stock_info_a_code_name()`` which returns a DataFrame with
        columns ``code`` and ``name``.  Industry and market information are
        not directly available from this endpoint, so they are left empty.
        """
        try:
            raw = ak.stock_info_a_code_name()
            if raw is None or raw.empty:
                return pd.DataFrame(columns=["code", "name", "industry", "market"])

            df = pd.DataFrame()
            df["code"] = raw["code"].astype(str)
            df["name"] = raw["name"].astype(str)
            # Industry is not provided by this endpoint
            df["industry"] = ""
            # Derive market from stock code prefix
            df["market"] = df["code"].apply(self._market_from_code)
            return df
        except Exception:
            logger.exception("AKShareSource.fetch_stock_list failed")
            return pd.DataFrame(columns=["code", "name", "industry", "market"])

    # ------------------------------------------------------------------
    # kline
    # ------------------------------------------------------------------

    def fetch_kline(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch daily kline data using ``ak.stock_zh_a_hist``.

        Parameters
        ----------
        stock_code : str
            Six-digit stock code, e.g. ``"000001"``.
        start_date, end_date : str
            Date strings in ``"YYYYMMDD"`` format.
        """
        try:
            raw = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if raw is None or raw.empty:
                return pd.DataFrame(
                    columns=[
                        "date", "open", "high", "low", "close",
                        "volume", "amount", "turnover", "change_pct",
                    ]
                )

            # AKShare returns Chinese column names; map to our standard.
            column_map = {
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
                "换手率": "turnover",
                "涨跌幅": "change_pct",
            }
            df = raw.rename(columns=column_map)
            # Keep only the standard columns that exist
            standard_cols = list(column_map.values())
            df = df[[c for c in standard_cols if c in df.columns]]
            return df
        except Exception:
            logger.exception(
                "AKShareSource.fetch_kline failed for %s", stock_code
            )
            return pd.DataFrame(
                columns=[
                    "date", "open", "high", "low", "close",
                    "volume", "amount", "turnover", "change_pct",
                ]
            )

    # ------------------------------------------------------------------
    # money flow
    # ------------------------------------------------------------------

    def fetch_money_flow(
        self,
        stock_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch money flow data using ``ak.stock_individual_fund_flow``.

        The *market* parameter is derived from the stock code prefix.
        """
        try:
            market = self._market_from_code(stock_code)
            market_param = "sh" if market == "SH" else "sz"
            raw = ak.stock_individual_fund_flow(
                stock=stock_code, market=market_param
            )
            if raw is None or raw.empty:
                return pd.DataFrame(
                    columns=[
                        "date", "main_net", "huge_net", "big_net",
                        "mid_net", "small_net",
                    ]
                )

            column_map = {
                "日期": "date",
                "主力净流入-净额": "main_net",
                "超大单净流入-净额": "huge_net",
                "大单净流入-净额": "big_net",
                "中单净流入-净额": "mid_net",
                "小单净流入-净额": "small_net",
            }
            df = raw.rename(columns=column_map)
            standard_cols = list(column_map.values())
            df = df[[c for c in standard_cols if c in df.columns]]

            # Optional date range filtering
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                if start_date:
                    df = df[df["date"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["date"] <= pd.to_datetime(end_date)]

            return df
        except Exception:
            logger.exception(
                "AKShareSource.fetch_money_flow failed for %s", stock_code
            )
            return pd.DataFrame(
                columns=[
                    "date", "main_net", "huge_net", "big_net",
                    "mid_net", "small_net",
                ]
            )

    # ------------------------------------------------------------------
    # news
    # ------------------------------------------------------------------

    def fetch_news(
        self, stock_code: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Fetch news articles using ``ak.stock_news_em``.

        If *stock_code* is ``None`` only an empty list is returned because
        the underlying API requires a stock symbol.
        """
        if stock_code is None:
            return []
        try:
            raw = ak.stock_news_em(symbol=stock_code)
            if raw is None or raw.empty:
                return []

            column_map = {
                "新闻标题": "title",
                "新闻内容": "content",
                "新闻来源": "source",
                "新闻链接": "url",
                "发布时间": "published_at",
            }
            df = raw.rename(columns=column_map)

            records: list[dict] = []
            for _, row in df.head(limit).iterrows():
                records.append(
                    {
                        "title": str(row.get("title", "")),
                        "content": str(row.get("content", "")),
                        "source": str(row.get("source", "")),
                        "url": str(row.get("url", "")),
                        "published_at": str(row.get("published_at", "")),
                    }
                )
            return records
        except Exception:
            logger.exception(
                "AKShareSource.fetch_news failed for %s", stock_code
            )
            return []

    # ------------------------------------------------------------------
    # financial report
    # ------------------------------------------------------------------

    def fetch_financial_report(self, stock_code: str) -> pd.DataFrame:
        """Fetch financial report data using ``ak.stock_financial_abstract_ths``.

        Column mapping is best-effort since AKShare financial endpoints
        change frequently.
        """
        empty = pd.DataFrame(
            columns=[
                "period", "pe_ratio", "pb_ratio", "roe", "revenue",
                "net_profit", "gross_margin", "debt_ratio", "report_date",
            ]
        )
        try:
            raw = ak.stock_financial_abstract_ths(symbol=stock_code)
            if raw is None or raw.empty:
                return empty

            column_map = {
                "报告期": "period",
                "市盈率": "pe_ratio",
                "市净率": "pb_ratio",
                "净资产收益率": "roe",
                "营业总收入": "revenue",
                "净利润": "net_profit",
                "毛利率": "gross_margin",
                "资产负债率": "debt_ratio",
                "公告日期": "report_date",
            }
            df = raw.rename(columns=column_map)
            standard_cols = list(column_map.values())
            df = df[[c for c in standard_cols if c in df.columns]]

            # Fill any missing standard columns with NaN
            for col in standard_cols:
                if col not in df.columns:
                    df[col] = None

            return df
        except Exception:
            logger.exception(
                "AKShareSource.fetch_financial_report failed for %s",
                stock_code,
            )
            return empty

    # ------------------------------------------------------------------
    # margin data
    # ------------------------------------------------------------------

    def fetch_margin_data(
        self,
        stock_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch margin trading data.

        Tries ``ak.stock_margin_detail_info`` (East Money) with best-effort
        column mapping.
        """
        empty = pd.DataFrame(
            columns=[
                "date", "margin_balance", "short_balance",
                "margin_buy", "margin_repay",
            ]
        )
        try:
            raw = ak.stock_margin_detail_info(symbol=stock_code)
            if raw is None or raw.empty:
                return empty

            column_map = {
                "日期": "date",
                "融资余额": "margin_balance",
                "融券余额": "short_balance",
                "融资买入额": "margin_buy",
                "融资偿还额": "margin_repay",
            }
            df = raw.rename(columns=column_map)
            standard_cols = list(column_map.values())
            df = df[[c for c in standard_cols if c in df.columns]]

            # Fill any missing standard columns with NaN
            for col in standard_cols:
                if col not in df.columns:
                    df[col] = None

            # Optional date range filtering
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                if start_date:
                    df = df[df["date"] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df["date"] <= pd.to_datetime(end_date)]

            return df
        except Exception:
            logger.exception(
                "AKShareSource.fetch_margin_data failed for %s", stock_code
            )
            return empty

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _market_from_code(code: str) -> str:
        """Derive market (SH/SZ/BJ) from the stock code prefix."""
        code = str(code)
        if code.startswith(("6",)):
            return "SH"
        if code.startswith(("0", "3")):
            return "SZ"
        if code.startswith(("4", "8")):
            return "BJ"
        return "SZ"
