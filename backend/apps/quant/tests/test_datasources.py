"""Tests for the quant data-source abstraction layer.

All external API calls (akshare, tushare) are mocked so that tests run
without network access and without any third-party API tokens.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from apps.quant.datasources.akshare_source import AKShareSource
from apps.quant.datasources.base import DataSourceBase
from apps.quant.datasources.router import DataSourceRouter
from apps.quant.datasources.tushare_source import TushareSource


# ======================================================================
# AKShareSource
# ======================================================================


class TestAKShareFetchStockList:
    """Test AKShareSource.fetch_stock_list with mocked akshare."""

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_dataframe_with_expected_columns(self, mock_ak):
        mock_ak.stock_info_a_code_name.return_value = pd.DataFrame(
            {
                "code": ["000001", "600519"],
                "name": ["平安银行", "贵州茅台"],
            }
        )

        source = AKShareSource()
        result = source.fetch_stock_list()

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["code", "name", "industry", "market"]
        assert len(result) == 2
        assert result.iloc[0]["code"] == "000001"
        assert result.iloc[0]["name"] == "平安银行"
        assert result.iloc[0]["market"] == "SZ"
        assert result.iloc[1]["market"] == "SH"

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_on_exception(self, mock_ak):
        mock_ak.stock_info_a_code_name.side_effect = RuntimeError("API down")

        source = AKShareSource()
        result = source.fetch_stock_list()

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == ["code", "name", "industry", "market"]


class TestAKShareFetchKline:
    """Test AKShareSource.fetch_kline with mocked akshare."""

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_dataframe_with_standard_columns(self, mock_ak):
        mock_ak.stock_zh_a_hist.return_value = pd.DataFrame(
            {
                "日期": ["2025-01-10", "2025-01-11"],
                "开盘": [10.5, 10.8],
                "最高": [11.0, 11.2],
                "最低": [10.2, 10.5],
                "收盘": [10.8, 11.0],
                "成交量": [1000000, 1200000],
                "成交额": [10800000, 13200000],
                "换手率": [1.5, 1.8],
                "涨跌幅": [2.86, 1.85],
                "振幅": [7.62, 6.48],
                "涨跌额": [0.3, 0.2],
            }
        )

        source = AKShareSource()
        result = source.fetch_kline("000001", "20250110", "20250111")

        assert isinstance(result, pd.DataFrame)
        expected_cols = [
            "date", "open", "high", "low", "close",
            "volume", "amount", "turnover", "change_pct",
        ]
        assert list(result.columns) == expected_cols
        assert len(result) == 2
        assert result.iloc[0]["open"] == 10.5
        assert result.iloc[0]["change_pct"] == 2.86

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_on_none(self, mock_ak):
        mock_ak.stock_zh_a_hist.return_value = None

        source = AKShareSource()
        result = source.fetch_kline("000001", "20250110", "20250111")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestAKShareFetchKlineError:
    """Test AKShareSource.fetch_kline error handling."""

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_dataframe_on_exception(self, mock_ak):
        mock_ak.stock_zh_a_hist.side_effect = ConnectionError("timeout")

        source = AKShareSource()
        result = source.fetch_kline("000001", "20250110", "20250111")

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        expected_cols = [
            "date", "open", "high", "low", "close",
            "volume", "amount", "turnover", "change_pct",
        ]
        assert list(result.columns) == expected_cols


class TestAKShareFetchMoneyFlow:
    """Test AKShareSource.fetch_money_flow with mocked akshare."""

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_dataframe_with_standard_columns(self, mock_ak):
        mock_ak.stock_individual_fund_flow.return_value = pd.DataFrame(
            {
                "日期": ["2025-01-10"],
                "收盘价": [10.8],
                "涨跌幅": [2.86],
                "主力净流入-净额": [5000000],
                "超大单净流入-净额": [3000000],
                "大单净流入-净额": [2000000],
                "中单净流入-净额": [-500000],
                "小单净流入-净额": [-1500000],
            }
        )

        source = AKShareSource()
        result = source.fetch_money_flow("000001")

        assert isinstance(result, pd.DataFrame)
        expected_cols = [
            "date", "main_net", "huge_net", "big_net",
            "mid_net", "small_net",
        ]
        assert list(result.columns) == expected_cols
        assert len(result) == 1
        assert result.iloc[0]["main_net"] == 5000000

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_on_exception(self, mock_ak):
        mock_ak.stock_individual_fund_flow.side_effect = RuntimeError("fail")

        source = AKShareSource()
        result = source.fetch_money_flow("000001")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestAKShareFetchNews:
    """Test AKShareSource.fetch_news with mocked akshare."""

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_list_of_dicts(self, mock_ak):
        mock_ak.stock_news_em.return_value = pd.DataFrame(
            {
                "新闻标题": ["平安银行发布年报", "银行板块走强"],
                "新闻内容": ["平安银行2025年业绩亮眼...", "多家银行股涨停..."],
                "新闻来源": ["新浪财经", "东方财富"],
                "新闻链接": [
                    "https://example.com/1",
                    "https://example.com/2",
                ],
                "发布时间": ["2025-01-10 10:00:00", "2025-01-10 11:00:00"],
            }
        )

        source = AKShareSource()
        result = source.fetch_news("000001")

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], dict)
        assert result[0]["title"] == "平安银行发布年报"
        assert result[0]["content"] == "平安银行2025年业绩亮眼..."
        assert result[0]["source"] == "新浪财经"
        assert result[0]["url"] == "https://example.com/1"
        assert result[0]["published_at"] == "2025-01-10 10:00:00"

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_list_when_no_stock_code(self, mock_ak):
        source = AKShareSource()
        result = source.fetch_news(stock_code=None)

        assert result == []
        mock_ak.stock_news_em.assert_not_called()

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_list_on_exception(self, mock_ak):
        mock_ak.stock_news_em.side_effect = RuntimeError("fail")

        source = AKShareSource()
        result = source.fetch_news("000001")

        assert result == []

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_respects_limit(self, mock_ak):
        mock_ak.stock_news_em.return_value = pd.DataFrame(
            {
                "新闻标题": [f"News {i}" for i in range(10)],
                "新闻内容": [f"Content {i}" for i in range(10)],
                "新闻来源": ["Source"] * 10,
                "新闻链接": [f"https://example.com/{i}" for i in range(10)],
                "发布时间": ["2025-01-10"] * 10,
            }
        )

        source = AKShareSource()
        result = source.fetch_news("000001", limit=3)

        assert len(result) == 3


class TestAKShareFetchFinancialReport:
    """Test AKShareSource.fetch_financial_report with mocked akshare."""

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_dataframe_on_success(self, mock_ak):
        mock_ak.stock_financial_abstract_ths.return_value = pd.DataFrame(
            {
                "报告期": ["2025Q3"],
                "净资产收益率": [12.5],
                "营业总收入": [1500000000],
                "净利润": [300000000],
            }
        )

        source = AKShareSource()
        result = source.fetch_financial_report("000001")

        assert isinstance(result, pd.DataFrame)
        assert "period" in result.columns
        assert "roe" in result.columns
        assert "revenue" in result.columns
        assert "net_profit" in result.columns
        assert len(result) == 1

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_on_exception(self, mock_ak):
        mock_ak.stock_financial_abstract_ths.side_effect = RuntimeError("fail")

        source = AKShareSource()
        result = source.fetch_financial_report("000001")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestAKShareFetchMarginData:
    """Test AKShareSource.fetch_margin_data with mocked akshare."""

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_dataframe_on_success(self, mock_ak):
        mock_ak.stock_margin_detail_info.return_value = pd.DataFrame(
            {
                "日期": ["2025-01-10"],
                "融资余额": [1000000000],
                "融券余额": [50000000],
                "融资买入额": [200000000],
                "融资偿还额": [180000000],
            }
        )

        source = AKShareSource()
        result = source.fetch_margin_data("000001")

        assert isinstance(result, pd.DataFrame)
        expected_cols = [
            "date", "margin_balance", "short_balance",
            "margin_buy", "margin_repay",
        ]
        assert list(result.columns) == expected_cols
        assert len(result) == 1

    @patch("apps.quant.datasources.akshare_source.ak")
    def test_returns_empty_on_exception(self, mock_ak):
        mock_ak.stock_margin_detail_info.side_effect = RuntimeError("fail")

        source = AKShareSource()
        result = source.fetch_margin_data("000001")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ======================================================================
# AKShareSource helpers
# ======================================================================


class TestAKShareMarketFromCode:
    def test_sh_codes(self):
        assert AKShareSource._market_from_code("600519") == "SH"
        assert AKShareSource._market_from_code("601318") == "SH"

    def test_sz_codes(self):
        assert AKShareSource._market_from_code("000001") == "SZ"
        assert AKShareSource._market_from_code("300750") == "SZ"

    def test_bj_codes(self):
        assert AKShareSource._market_from_code("430047") == "BJ"
        assert AKShareSource._market_from_code("830799") == "BJ"


# ======================================================================
# TushareSource
# ======================================================================


class TestTushareUnavailable:
    """Test TushareSource when tushare is not installed or no token given."""

    def test_no_token_returns_empty_stock_list(self):
        source = TushareSource(token="")
        result = source.fetch_stock_list()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_no_token_returns_empty_kline(self):
        source = TushareSource(token="")
        result = source.fetch_kline("000001", "20250110", "20250111")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_no_token_returns_empty_money_flow(self):
        source = TushareSource(token="")
        result = source.fetch_money_flow("000001")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_no_token_returns_empty_news(self):
        source = TushareSource(token="")
        result = source.fetch_news("000001")
        assert result == []

    def test_no_token_returns_empty_financial_report(self):
        source = TushareSource(token="")
        result = source.fetch_financial_report("000001")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_no_token_returns_empty_margin_data(self):
        source = TushareSource(token="")
        result = source.fetch_margin_data("000001")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_available_is_false(self):
        source = TushareSource(token="")
        assert source.available is False


class TestTushareCodeConversion:
    """Test the _to_ts_code helper."""

    def test_sz_code(self):
        assert TushareSource._to_ts_code("000001") == "000001.SZ"

    def test_sh_code(self):
        assert TushareSource._to_ts_code("600519") == "600519.SH"

    def test_gem_code(self):
        assert TushareSource._to_ts_code("300750") == "300750.SZ"

    def test_bj_code(self):
        assert TushareSource._to_ts_code("430047") == "430047.BJ"


# ======================================================================
# DataSourceRouter
# ======================================================================


class _FakeSource(DataSourceBase):
    """Minimal fake source for router tests."""

    def __init__(self, kline_data=None, should_raise=False):
        self._kline_data = kline_data
        self._should_raise = should_raise

    def fetch_stock_list(self):
        return pd.DataFrame()

    def fetch_kline(self, stock_code, start_date, end_date):
        if self._should_raise:
            raise RuntimeError("Simulated failure")
        if self._kline_data is not None:
            return self._kline_data
        return pd.DataFrame()

    def fetch_money_flow(self, stock_code, start_date=None, end_date=None):
        return pd.DataFrame()

    def fetch_news(self, stock_code=None, limit=50):
        return []

    def fetch_financial_report(self, stock_code):
        return pd.DataFrame()

    def fetch_margin_data(self, stock_code, start_date=None, end_date=None):
        return pd.DataFrame()


class TestRouterFailover:
    """Test that the router falls through to the next source on failure."""

    def test_tries_next_source_on_exception(self):
        good_data = pd.DataFrame(
            {
                "date": ["2025-01-10"],
                "open": [10.5],
                "high": [11.0],
                "low": [10.2],
                "close": [10.8],
                "volume": [1000000],
                "amount": [10800000],
                "turnover": [1.5],
                "change_pct": [2.86],
            }
        )
        failing_source = _FakeSource(should_raise=True)
        good_source = _FakeSource(kline_data=good_data)

        router = DataSourceRouter(sources=[failing_source, good_source])
        result = router.fetch_kline("000001", "20250110", "20250110")

        assert not result.empty
        assert result.iloc[0]["close"] == 10.8

    def test_returns_empty_when_all_fail(self):
        s1 = _FakeSource(should_raise=True)
        s2 = _FakeSource(should_raise=True)

        router = DataSourceRouter(sources=[s1, s2])
        result = router.fetch_kline("000001", "20250110", "20250110")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestRouterReturnsFirstSuccess:
    """Test that the router stops at the first successful source."""

    def test_returns_result_from_first_successful_source(self):
        first_data = pd.DataFrame(
            {
                "date": ["2025-01-10"],
                "open": [10.5],
                "high": [11.0],
                "low": [10.2],
                "close": [10.8],
                "volume": [1000000],
                "amount": [10800000],
                "turnover": [1.5],
                "change_pct": [2.86],
            }
        )
        second_data = pd.DataFrame(
            {
                "date": ["2025-01-10"],
                "open": [99.0],
                "high": [99.0],
                "low": [99.0],
                "close": [99.0],
                "volume": [99],
                "amount": [99],
                "turnover": [99],
                "change_pct": [99],
            }
        )
        source_a = _FakeSource(kline_data=first_data)
        source_b = _FakeSource(kline_data=second_data)

        router = DataSourceRouter(sources=[source_a, source_b])
        result = router.fetch_kline("000001", "20250110", "20250110")

        # Must come from the first source
        assert result.iloc[0]["close"] == 10.8

    def test_skips_empty_results(self):
        """First source returns empty; second source should be used."""
        empty_source = _FakeSource(kline_data=pd.DataFrame())
        good_data = pd.DataFrame(
            {
                "date": ["2025-01-10"],
                "open": [10.5],
                "high": [11.0],
                "low": [10.2],
                "close": [10.8],
                "volume": [1000000],
                "amount": [10800000],
                "turnover": [1.5],
                "change_pct": [2.86],
            }
        )
        good_source = _FakeSource(kline_data=good_data)

        router = DataSourceRouter(sources=[empty_source, good_source])
        result = router.fetch_kline("000001", "20250110", "20250110")

        assert not result.empty
        assert result.iloc[0]["close"] == 10.8


class TestRouterNewsFailover:
    """Test router failover for the news endpoint (list, not DataFrame)."""

    def test_news_failover(self):
        class _NewsSource(DataSourceBase):
            def __init__(self, news=None, should_raise=False):
                self._news = news or []
                self._should_raise = should_raise

            def fetch_stock_list(self):
                return pd.DataFrame()

            def fetch_kline(self, *a, **kw):
                return pd.DataFrame()

            def fetch_money_flow(self, *a, **kw):
                return pd.DataFrame()

            def fetch_news(self, stock_code=None, limit=50):
                if self._should_raise:
                    raise RuntimeError("boom")
                return self._news

            def fetch_financial_report(self, *a, **kw):
                return pd.DataFrame()

            def fetch_margin_data(self, *a, **kw):
                return pd.DataFrame()

        failing = _NewsSource(should_raise=True)
        good = _NewsSource(
            news=[{"title": "Test", "content": "", "source": "",
                   "url": "", "published_at": ""}]
        )
        router = DataSourceRouter(sources=[failing, good])
        result = router.fetch_news("000001")

        assert len(result) == 1
        assert result[0]["title"] == "Test"


# ======================================================================
# Interface compliance
# ======================================================================


class TestInterfaceCompliance:
    """Verify that concrete sources are valid DataSourceBase subclasses."""

    def test_akshare_source_is_datasource(self):
        assert issubclass(AKShareSource, DataSourceBase)

    def test_tushare_source_is_datasource(self):
        assert issubclass(TushareSource, DataSourceBase)
