"""Tests for quant API endpoints (stocks, analysis, recommendations, config, tasks)."""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http_status
from rest_framework.test import APIClient

from apps.quant.analyzers.types import Signal, TradingStyle
from apps.quant.models import (
    FinancialReport,
    KlineData,
    MoneyFlow,
    NewsArticle,
    StockBasic,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin", email="admin@e.com", password="pass123", role="admin"
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="regular", email="r@e.com", password="pass123", role="visitor"
    )


@pytest.fixture
def api_client(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    return client


@pytest.fixture
def regular_client(regular_user):
    client = APIClient()
    client.force_authenticate(regular_user)
    return client


@pytest.fixture
def stock(db):
    return StockBasic.objects.create(
        code="000001",
        name="Ping An Bank",
        industry="Banking",
        sector="Finance",
        market="SZ",
        list_date=date(1991, 4, 3),
        is_active=True,
    )


@pytest.fixture
def stock2(db):
    return StockBasic.objects.create(
        code="600519",
        name="Kweichow Moutai",
        industry="Liquor",
        sector="Consumer",
        market="SH",
        list_date=date(2001, 8, 27),
        is_active=True,
    )


@pytest.fixture
def inactive_stock(db):
    return StockBasic.objects.create(
        code="000999",
        name="Inactive Corp",
        industry="Other",
        sector="Other",
        market="SZ",
        is_active=False,
    )


@pytest.fixture
def kline_data(stock):
    klines = []
    for i in range(5):
        klines.append(
            KlineData.objects.create(
                stock=stock,
                date=date(2025, 1, 10 - i),
                open=Decimal("10.00") + i,
                high=Decimal("11.00") + i,
                low=Decimal("9.50") + i,
                close=Decimal("10.50") + i,
                volume=1000000 + i * 100000,
                amount=Decimal("10500000.0000"),
                turnover=Decimal("1.5000"),
                change_pct=Decimal("1.2000"),
            )
        )
    return klines


@pytest.fixture
def money_flow_data(stock):
    flows = []
    for i in range(3):
        flows.append(
            MoneyFlow.objects.create(
                stock=stock,
                date=date(2025, 1, 10 - i),
                main_net=Decimal("1000000.0000"),
                huge_net=Decimal("500000.0000"),
                big_net=Decimal("300000.0000"),
                mid_net=Decimal("-200000.0000"),
                small_net=Decimal("-100000.0000"),
            )
        )
    return flows


@pytest.fixture
def financial_data(stock):
    reports = []
    for period in ["2024Q3", "2024Q2", "2024Q1"]:
        reports.append(
            FinancialReport.objects.create(
                stock=stock,
                period=period,
                pe_ratio=Decimal("8.5000"),
                pb_ratio=Decimal("0.9000"),
                roe=Decimal("12.5000"),
                revenue=Decimal("1500000000.0000"),
                net_profit=Decimal("300000000.0000"),
                gross_margin=Decimal("45.0000"),
                debt_ratio=Decimal("88.0000"),
                report_date=date(2024, 10, 30),
            )
        )
    return reports


@pytest.fixture
def news_data(stock):
    articles = []
    for i in range(3):
        articles.append(
            NewsArticle.objects.create(
                stock=stock,
                title=f"News article {i}",
                content=f"Content for article {i}",
                source="Reuters",
                url=f"https://example.com/news/{i}",
                sentiment_score=Decimal("0.7500"),
                published_at=datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
    return articles


# ---------------------------------------------------------------------------
# Helper: mock scorer result
# ---------------------------------------------------------------------------


def _mock_score_result(
    score=75.0, signal=Signal.BUY, confidence=0.8, style=TradingStyle.SWING
):
    return {
        "final_score": score,
        "signal": signal,
        "confidence": confidence,
        "style": style,
        "explanation": "test explanation",
        "analyzer_results": {},
        "component_scores": {"technical": 30, "fundamental": 10},
    }


def _mock_trading_signal():
    mock_signal = MagicMock()
    mock_signal.entry_price = 10.0
    mock_signal.stop_loss = 9.0
    mock_signal.take_profit = 13.0
    mock_signal.position_pct = 5.0
    mock_signal.risk_reward_ratio = 3.0
    return mock_signal


# ===========================================================================
# Stock Data Endpoints
# ===========================================================================


class TestStockList:
    """Tests for GET /api/quant/stocks/"""

    def test_stock_list(self, api_client, stock, stock2):
        response = api_client.get("/api/quant/stocks/")
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data["results"]) == 2

    def test_stock_list_search(self, api_client, stock, stock2):
        response = api_client.get("/api/quant/stocks/", {"search": "Ping An"})
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["code"] == "000001"

    def test_stock_list_search_by_code(self, api_client, stock, stock2):
        response = api_client.get("/api/quant/stocks/", {"search": "600519"})
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["code"] == "600519"

    def test_stock_list_filter_market(self, api_client, stock, stock2):
        response = api_client.get("/api/quant/stocks/", {"market": "SZ"})
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["market"] == "SZ"

    def test_stock_list_filter_is_active(self, api_client, stock, inactive_stock):
        response = api_client.get("/api/quant/stocks/", {"is_active": "true"})
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["is_active"] is True


class TestStockDetail:
    """Tests for GET /api/quant/stocks/{code}/"""

    def test_stock_detail(self, api_client, stock):
        response = api_client.get("/api/quant/stocks/000001/")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["code"] == "000001"
        assert response.data["name"] == "Ping An Bank"
        assert response.data["industry"] == "Banking"

    def test_stock_detail_not_found(self, api_client):
        response = api_client.get("/api/quant/stocks/999999/")
        assert response.status_code == http_status.HTTP_404_NOT_FOUND


class TestKlineData:
    """Tests for GET /api/quant/stocks/{code}/kline/"""

    def test_kline_data(self, api_client, stock, kline_data):
        response = api_client.get("/api/quant/stocks/000001/kline/")
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 5

    def test_kline_data_with_days_param(self, api_client, stock, kline_data):
        response = api_client.get("/api/quant/stocks/000001/kline/", {"days": "3"})
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 3

    def test_kline_data_empty(self, api_client, stock):
        response = api_client.get("/api/quant/stocks/000001/kline/")
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 0


class TestMoneyFlowData:
    """Tests for GET /api/quant/stocks/{code}/money-flow/"""

    def test_money_flow_data(self, api_client, stock, money_flow_data):
        response = api_client.get("/api/quant/stocks/000001/money-flow/")
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 3

    def test_money_flow_with_days(self, api_client, stock, money_flow_data):
        response = api_client.get(
            "/api/quant/stocks/000001/money-flow/", {"days": "2"}
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 2


class TestFinancialReports:
    """Tests for GET /api/quant/stocks/{code}/financials/"""

    def test_financial_reports(self, api_client, stock, financial_data):
        response = api_client.get("/api/quant/stocks/000001/financials/")
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 3
        # Check it includes expected fields
        first = response.data[0]
        assert "period" in first
        assert "pe_ratio" in first
        assert "roe" in first


class TestStockNews:
    """Tests for GET /api/quant/stocks/{code}/news/"""

    def test_stock_news(self, api_client, stock, news_data):
        response = api_client.get("/api/quant/stocks/000001/news/")
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 3

    def test_stock_news_with_limit(self, api_client, stock, news_data):
        response = api_client.get("/api/quant/stocks/000001/news/", {"limit": "1"})
        assert response.status_code == http_status.HTTP_200_OK
        assert len(response.data) == 1


# ===========================================================================
# Analysis Endpoints
# ===========================================================================


class TestStockAnalysis:
    """Tests for POST /api/quant/analysis/"""

    @patch("apps.quant.analyzers.SignalGenerator")
    @patch("apps.quant.analyzers.MultiFactorScorer")
    def test_stock_analysis(self, MockScorer, MockSignalGen, api_client, stock):
        mock_scorer_instance = MockScorer.return_value
        mock_scorer_instance.score.return_value = _mock_score_result()

        mock_signal_gen_instance = MockSignalGen.return_value
        mock_signal_gen_instance.generate.return_value = _mock_trading_signal()

        response = api_client.post(
            "/api/quant/analysis/",
            {"stock_code": "000001", "style": "swing"},
            format="json",
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["stock_code"] == "000001"
        assert response.data["style"] == "swing"
        assert response.data["score"] == 75.0
        assert response.data["signal"] == "BUY"
        assert response.data["confidence"] == 0.8
        assert response.data["entry_price"] == 10.0
        assert response.data["stop_loss"] == 9.0
        assert response.data["take_profit"] == 13.0
        assert response.data["component_scores"] == {"technical": 30, "fundamental": 10}

    def test_stock_analysis_missing_stock_code(self, api_client):
        response = api_client.post(
            "/api/quant/analysis/",
            {"style": "swing"},
            format="json",
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_stock_analysis_invalid_style(self, api_client):
        response = api_client.post(
            "/api/quant/analysis/",
            {"stock_code": "000001", "style": "invalid"},
            format="json",
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


class TestRecommendations:
    """Tests for GET /api/quant/recommendations/"""

    @patch("apps.quant.analyzers.SignalGenerator")
    @patch("apps.quant.analyzers.MultiFactorScorer")
    def test_recommendations(self, MockScorer, MockSignalGen, api_client, stock):
        mock_scorer_instance = MockScorer.return_value
        mock_scorer_instance.score.return_value = _mock_score_result()

        mock_signal_gen_instance = MockSignalGen.return_value
        mock_signal_gen_instance.generate.return_value = _mock_trading_signal()

        response = api_client.get("/api/quant/recommendations/")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["style"] == "swing"
        assert response.data["count"] >= 1
        assert len(response.data["results"]) >= 1

        result = response.data["results"][0]
        assert result["stock_code"] == "000001"
        assert result["stock_name"] == "Ping An Bank"
        assert result["signal"] == "BUY"

    @patch("apps.quant.analyzers.SignalGenerator")
    @patch("apps.quant.analyzers.MultiFactorScorer")
    def test_recommendations_with_signal_filter(
        self, MockScorer, MockSignalGen, api_client, stock
    ):
        mock_scorer_instance = MockScorer.return_value
        mock_scorer_instance.score.return_value = _mock_score_result(
            signal=Signal.HOLD, score=50.0
        )

        mock_signal_gen_instance = MockSignalGen.return_value
        mock_signal_gen_instance.generate.return_value = _mock_trading_signal()

        # Filter for BUY only, but our mock returns HOLD -> no results
        response = api_client.get(
            "/api/quant/recommendations/", {"signal": "BUY"}
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["count"] == 0

    @patch("apps.quant.analyzers.SignalGenerator")
    @patch("apps.quant.analyzers.MultiFactorScorer")
    def test_recommendations_with_min_score(
        self, MockScorer, MockSignalGen, api_client, stock
    ):
        mock_scorer_instance = MockScorer.return_value
        mock_scorer_instance.score.return_value = _mock_score_result(score=40.0)

        mock_signal_gen_instance = MockSignalGen.return_value
        mock_signal_gen_instance.generate.return_value = _mock_trading_signal()

        # min_score=50 but mock returns 40 -> no results
        response = api_client.get(
            "/api/quant/recommendations/", {"min_score": "50"}
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["count"] == 0

    @patch("apps.quant.analyzers.SignalGenerator")
    @patch("apps.quant.analyzers.MultiFactorScorer")
    def test_recommendations_excludes_inactive_stocks(
        self, MockScorer, MockSignalGen, api_client, stock, inactive_stock
    ):
        mock_scorer_instance = MockScorer.return_value
        mock_scorer_instance.score.return_value = _mock_score_result()

        mock_signal_gen_instance = MockSignalGen.return_value
        mock_signal_gen_instance.generate.return_value = _mock_trading_signal()

        response = api_client.get("/api/quant/recommendations/")
        assert response.status_code == http_status.HTTP_200_OK
        # Only active stock should appear
        codes = [r["stock_code"] for r in response.data["results"]]
        assert "000001" in codes
        assert "000999" not in codes


class TestAIReport:
    """Tests for POST /api/quant/ai-report/"""

    @patch("apps.quant.analyzers.AIAnalyzer")
    @patch("apps.quant.analyzers.MultiFactorScorer")
    def test_ai_report(self, MockScorer, MockAI, api_client, stock):
        mock_scorer_instance = MockScorer.return_value
        mock_scorer_instance.score.return_value = _mock_score_result()

        mock_ai_instance = MockAI.return_value
        mock_ai_instance.generate_report.return_value = {
            "summary": "Bullish outlook",
            "risk_factors": ["Market volatility"],
        }

        response = api_client.post(
            "/api/quant/ai-report/",
            {"stock_code": "000001"},
            format="json",
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["stock_code"] == "000001"
        assert "report" in response.data
        assert response.data["report"]["summary"] == "Bullish outlook"
        assert "analysis_summary" in response.data
        assert response.data["analysis_summary"]["score"] == 75.0

    def test_ai_report_missing_stock_code(self, api_client):
        response = api_client.post(
            "/api/quant/ai-report/",
            {},
            format="json",
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "stock_code is required"


# ===========================================================================
# Config Endpoints
# ===========================================================================


class TestFactorWeights:
    """Tests for GET/PUT /api/quant/config/weights/"""

    def test_get_factor_weights(self, api_client):
        response = api_client.get("/api/quant/config/weights/")
        assert response.status_code == http_status.HTTP_200_OK
        assert "swing" in response.data
        assert "ultra_short" in response.data
        assert "mid_long" in response.data
        # Verify weights structure
        swing_weights = response.data["swing"]
        assert "technical" in swing_weights
        assert "fundamental" in swing_weights

    def test_put_factor_weights_valid(self, api_client):
        response = api_client.put(
            "/api/quant/config/weights/",
            {
                "style": "swing",
                "weights": {
                    "technical": 0.3,
                    "fundamental": 0.2,
                    "money_flow": 0.15,
                    "chip": 0.15,
                    "sentiment": 0.1,
                    "sector_rotation": 0.05,
                    "behavior_finance": 0.025,
                    "ai": 0.025,
                },
            },
            format="json",
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["style"] == "swing"
        assert "weights" in response.data

    def test_put_factor_weights_invalid_sum(self, api_client):
        response = api_client.put(
            "/api/quant/config/weights/",
            {
                "style": "swing",
                "weights": {
                    "technical": 0.5,
                    "fundamental": 0.5,
                    "money_flow": 0.5,
                },
            },
            format="json",
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Weights must sum to 1.0" in response.data["error"]

    def test_put_factor_weights_missing_style(self, api_client):
        response = api_client.put(
            "/api/quant/config/weights/",
            {"weights": {"technical": 1.0}},
            format="json",
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST


# ===========================================================================
# Task Monitoring
# ===========================================================================


class TestTaskMonitor:
    """Tests for GET/POST /api/quant/tasks/"""

    def test_get_tasks(self, api_client):
        response = api_client.get("/api/quant/tasks/")
        assert response.status_code == http_status.HTTP_200_OK
        assert "beat_schedule" in response.data
        assert "schedule_count" in response.data
        assert response.data["schedule_count"] > 0
        # Check specific schedule entry
        schedule = response.data["beat_schedule"]
        assert "run-analysis-pipeline" in schedule
        assert schedule["run-analysis-pipeline"]["task"] == "quant.run_analysis_pipeline"

    @patch("celery.current_app")
    def test_trigger_task(self, mock_celery, api_client):
        mock_result = MagicMock()
        mock_result.id = "abc-123"
        mock_celery.send_task.return_value = mock_result

        response = api_client.post(
            "/api/quant/tasks/",
            {"task": "sync_stock_list"},
            format="json",
        )
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["task_name"] == "sync_stock_list"
        assert response.data["task_id"] == "abc-123"
        assert response.data["status"] == "PENDING"

    def test_trigger_unknown_task(self, api_client):
        response = api_client.post(
            "/api/quant/tasks/",
            {"task": "nonexistent_task"},
            format="json",
        )
        assert response.status_code == http_status.HTTP_400_BAD_REQUEST
        assert "Unknown task" in response.data["error"]
        assert "available" in response.data


# ===========================================================================
# Authentication & Authorization
# ===========================================================================


class TestAuth:
    """Tests for authentication and authorization."""

    def test_unauthenticated_access(self, db):
        client = APIClient()
        response = client.get("/api/quant/stocks/")
        assert response.status_code in (
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
        )

    def test_non_admin_access(self, regular_client, stock):
        response = regular_client.get("/api/quant/stocks/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_run_analysis(self, regular_client):
        response = regular_client.post(
            "/api/quant/analysis/",
            {"stock_code": "000001", "style": "swing"},
            format="json",
        )
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_access_tasks(self, regular_client):
        response = regular_client.get("/api/quant/tasks/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_access_weights(self, regular_client):
        response = regular_client.get("/api/quant/config/weights/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
