import logging

import pandas as pd

from .base import DataSourceBase

logger = logging.getLogger(__name__)

try:
    import tushare as ts

    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False


class TushareSource(DataSourceBase):
    """Supplementary data source using Tushare Pro.

    Tushare is entirely optional.  If the ``tushare`` package is not
    installed **or** no valid *token* is provided, every method silently
    returns an empty DataFrame / list so the :class:`DataSourceRouter` can
    fall through to the next source.
    """

    def __init__(self, token: str = ""):
        self.token = token
        self.pro = None
        if HAS_TUSHARE and token:
            try:
                ts.set_token(token)
                self.pro = ts.pro_api(token)
            except Exception:
                logger.exception("Failed to initialise Tushare Pro API")
                self.pro = None

    @property
    def available(self) -> bool:
        """Return ``True`` if the Tushare client is ready."""
        return self.pro is not None

    # ------------------------------------------------------------------
    # stock list
    # ------------------------------------------------------------------

    def fetch_stock_list(self) -> pd.DataFrame:
        empty = pd.DataFrame(columns=["code", "name", "industry", "market"])
        if not self.available:
            return empty
        try:
            raw = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,industry,market",
            )
            if raw is None or raw.empty:
                return empty

            df = pd.DataFrame()
            df["code"] = raw["symbol"].astype(str)
            df["name"] = raw["name"].astype(str)
            df["industry"] = raw.get("industry", "").astype(str)
            # Tushare market field uses SSE/SZSE; normalise to SH/SZ
            market_map = {"SSE": "SH", "SZSE": "SZ", "BSE": "BJ"}
            df["market"] = (
                raw["market"].map(market_map).fillna(raw["market"]).astype(str)
            )
            return df
        except Exception:
            logger.exception("TushareSource.fetch_stock_list failed")
            return empty

    # ------------------------------------------------------------------
    # kline
    # ------------------------------------------------------------------

    def fetch_kline(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        empty = pd.DataFrame(
            columns=[
                "date", "open", "high", "low", "close",
                "volume", "amount", "turnover", "change_pct",
            ]
        )
        if not self.available:
            return empty
        try:
            ts_code = self._to_ts_code(stock_code)
            raw = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if raw is None or raw.empty:
                return empty

            df = pd.DataFrame()
            df["date"] = pd.to_datetime(raw["trade_date"], format="%Y%m%d")
            df["open"] = raw["open"]
            df["high"] = raw["high"]
            df["low"] = raw["low"]
            df["close"] = raw["close"]
            df["volume"] = raw["vol"]
            df["amount"] = raw["amount"]
            df["turnover"] = None  # not directly in daily endpoint
            df["change_pct"] = raw["pct_chg"]
            return df.sort_values("date").reset_index(drop=True)
        except Exception:
            logger.exception(
                "TushareSource.fetch_kline failed for %s", stock_code
            )
            return empty

    # ------------------------------------------------------------------
    # money flow
    # ------------------------------------------------------------------

    def fetch_money_flow(
        self,
        stock_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        empty = pd.DataFrame(
            columns=[
                "date", "main_net", "huge_net", "big_net",
                "mid_net", "small_net",
            ]
        )
        if not self.available:
            return empty
        try:
            ts_code = self._to_ts_code(stock_code)
            kwargs: dict = {"ts_code": ts_code}
            if start_date:
                kwargs["start_date"] = start_date
            if end_date:
                kwargs["end_date"] = end_date

            raw = self.pro.moneyflow_dc(**kwargs)
            if raw is None or raw.empty:
                return empty

            df = pd.DataFrame()
            df["date"] = pd.to_datetime(raw["trade_date"], format="%Y%m%d")
            df["main_net"] = raw["net_amount"]
            df["huge_net"] = raw["buy_elg_amount"]
            df["big_net"] = raw["buy_lg_amount"]
            df["mid_net"] = raw["buy_md_amount"]
            df["small_net"] = raw["buy_sm_amount"]
            return df.sort_values("date").reset_index(drop=True)
        except Exception:
            logger.exception(
                "TushareSource.fetch_money_flow failed for %s", stock_code
            )
            return empty

    # ------------------------------------------------------------------
    # news
    # ------------------------------------------------------------------

    def fetch_news(
        self, stock_code: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Tushare Pro does not offer a direct per-stock news API.

        Returns an empty list so the router falls through to AKShare.
        """
        return []

    # ------------------------------------------------------------------
    # financial report
    # ------------------------------------------------------------------

    def fetch_financial_report(self, stock_code: str) -> pd.DataFrame:
        empty = pd.DataFrame(
            columns=[
                "period", "pe_ratio", "pb_ratio", "roe", "revenue",
                "net_profit", "gross_margin", "debt_ratio", "report_date",
            ]
        )
        if not self.available:
            return empty
        try:
            ts_code = self._to_ts_code(stock_code)
            raw = self.pro.fina_indicator(
                ts_code=ts_code,
                fields=(
                    "ann_date,end_date,pe,pb,roe,revenue,"
                    "netprofit,grossprofit_margin,debt_to_assets"
                ),
            )
            if raw is None or raw.empty:
                return empty

            df = pd.DataFrame()
            df["period"] = raw["end_date"].astype(str)
            df["pe_ratio"] = raw.get("pe")
            df["pb_ratio"] = raw.get("pb")
            df["roe"] = raw.get("roe")
            df["revenue"] = raw.get("revenue")
            df["net_profit"] = raw.get("netprofit")
            df["gross_margin"] = raw.get("grossprofit_margin")
            df["debt_ratio"] = raw.get("debt_to_assets")
            df["report_date"] = pd.to_datetime(
                raw.get("ann_date"), format="%Y%m%d", errors="coerce"
            )
            return df
        except Exception:
            logger.exception(
                "TushareSource.fetch_financial_report failed for %s",
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
        empty = pd.DataFrame(
            columns=[
                "date", "margin_balance", "short_balance",
                "margin_buy", "margin_repay",
            ]
        )
        if not self.available:
            return empty
        try:
            ts_code = self._to_ts_code(stock_code)
            kwargs: dict = {"ts_code": ts_code}
            if start_date:
                kwargs["start_date"] = start_date
            if end_date:
                kwargs["end_date"] = end_date

            raw = self.pro.margin_detail(**kwargs)
            if raw is None or raw.empty:
                return empty

            df = pd.DataFrame()
            df["date"] = pd.to_datetime(raw["trade_date"], format="%Y%m%d")
            df["margin_balance"] = raw["rzye"]
            df["short_balance"] = raw["rqye"]
            df["margin_buy"] = raw["rzmre"]
            df["margin_repay"] = raw["rzche"]
            return df.sort_values("date").reset_index(drop=True)
        except Exception:
            logger.exception(
                "TushareSource.fetch_margin_data failed for %s", stock_code
            )
            return empty

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_ts_code(stock_code: str) -> str:
        """Convert a plain six-digit code to Tushare format (e.g. 000001.SZ)."""
        code = str(stock_code).zfill(6)
        if code.startswith("6"):
            return f"{code}.SH"
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        if code.startswith(("4", "8")):
            return f"{code}.BJ"
        return f"{code}.SZ"
