"""DRF views for quant data and analysis APIs."""

import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

logger = logging.getLogger(__name__)

from .models import FinancialReport, KlineData, MoneyFlow, NewsArticle, StockBasic
from .serializers import (
    FactorWeightSerializer,
    FinancialReportSerializer,
    KlineDataSerializer,
    MoneyFlowSerializer,
    NewsArticleSerializer,
    RecommendationFilterSerializer,
    StockAnalysisRequestSerializer,
    StockBasicSerializer,
    StockCodeRequestSerializer,
)


class StockListView(generics.ListAPIView):
    """GET /api/quant/stocks/ - List all stocks with search/filter."""

    serializer_class = StockBasicSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["market", "industry", "is_active"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "industry"]

    def get_queryset(self):
        return StockBasic.objects.all()


class StockDetailView(generics.RetrieveAPIView):
    """GET /api/quant/stocks/{code}/ - Stock detail with recent data."""

    serializer_class = StockBasicSerializer
    permission_classes = [IsAdmin]
    lookup_field = "code"
    queryset = StockBasic.objects.all()


class KlineDataView(APIView):
    """GET /api/quant/stocks/{code}/kline/ - K-line data for a stock.

    Query params: days (default 120)
    """

    permission_classes = [IsAdmin]

    def get(self, request, code):
        try:
            days = int(request.query_params.get("days", 120))
            if days < 1 or days > 1000:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "days must be a positive integer (max 1000)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        klines = KlineData.objects.filter(stock_id=code).order_by("-date")[:days]
        serializer = KlineDataSerializer(klines, many=True)
        return Response(serializer.data)


class MoneyFlowView(APIView):
    """GET /api/quant/stocks/{code}/money-flow/ - Money flow data."""

    permission_classes = [IsAdmin]

    def get(self, request, code):
        try:
            days = int(request.query_params.get("days", 20))
            if days < 1 or days > 365:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "days must be a positive integer (max 365)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        flows = MoneyFlow.objects.filter(stock_id=code).order_by("-date")[:days]
        serializer = MoneyFlowSerializer(flows, many=True)
        return Response(serializer.data)


class FinancialReportView(APIView):
    """GET /api/quant/stocks/{code}/financials/ - Financial reports."""

    permission_classes = [IsAdmin]

    def get(self, request, code):
        reports = FinancialReport.objects.filter(stock_id=code).order_by("-period")[:8]
        serializer = FinancialReportSerializer(reports, many=True)
        return Response(serializer.data)


class StockNewsView(APIView):
    """GET /api/quant/stocks/{code}/news/ - News articles for a stock."""

    permission_classes = [IsAdmin]

    def get(self, request, code):
        try:
            limit = int(request.query_params.get("limit", 20))
            if limit < 1 or limit > 100:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "limit must be a positive integer (max 100)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        articles = NewsArticle.objects.filter(stock_id=code).order_by("-published_at")[
            :limit
        ]
        serializer = NewsArticleSerializer(articles, many=True)
        return Response(serializer.data)


class StockAnalysisView(APIView):
    """POST /api/quant/analysis/ - Run multi-factor analysis for a stock.

    Request body: { "stock_code": "000001", "style": "swing" }
    Runs synchronously and returns full analysis results.
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = StockAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stock_code = serializer.validated_data["stock_code"]
        style = serializer.validated_data["style"]

        from .analyzers import MultiFactorScorer, SignalGenerator, TradingStyle

        style_map = {
            "ultra_short": TradingStyle.ULTRA_SHORT,
            "swing": TradingStyle.SWING,
            "mid_long": TradingStyle.MID_LONG,
        }

        scorer = MultiFactorScorer(style=style_map[style])
        signal_gen = SignalGenerator()

        score_result = scorer.score(stock_code)
        signal = signal_gen.generate(stock_code, score_result)

        return Response(
            {
                "stock_code": stock_code,
                "style": style,
                "score": score_result["final_score"],
                "signal": score_result["signal"].value,
                "confidence": score_result["confidence"],
                "explanation": score_result["explanation"],
                "component_scores": score_result["component_scores"],
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "position_pct": signal.position_pct,
                "risk_reward_ratio": signal.risk_reward_ratio,
            }
        )


class RecommendationsView(APIView):
    """GET /api/quant/recommendations/ - Get stock recommendations.

    Query params: style, signal, min_score, limit
    Runs analysis pipeline on active stocks and returns filtered results.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        filter_ser = RecommendationFilterSerializer(data=request.query_params)
        filter_ser.is_valid(raise_exception=True)
        params = filter_ser.validated_data

        style = params.get("style", "swing")
        signal_filter = params.get("signal")
        min_score = params.get("min_score", 0)
        limit = params.get("limit", 20)

        from .analyzers import MultiFactorScorer, SignalGenerator, TradingStyle

        style_map = {
            "ultra_short": TradingStyle.ULTRA_SHORT,
            "swing": TradingStyle.SWING,
            "mid_long": TradingStyle.MID_LONG,
        }

        scorer = MultiFactorScorer(style=style_map[style])
        signal_gen = SignalGenerator()

        stocks = StockBasic.objects.filter(is_active=True)
        stock_map = {s.code: s for s in stocks}

        results = []
        for code, stock in list(stock_map.items())[:200]:
            try:
                score_result = scorer.score(code)
                if score_result["final_score"] < min_score:
                    continue
                if signal_filter and score_result["signal"].value != signal_filter:
                    continue

                signal = signal_gen.generate(code, score_result)

                results.append(
                    {
                        "stock_code": code,
                        "stock_name": stock.name,
                        "industry": stock.industry,
                        "score": score_result["final_score"],
                        "signal": score_result["signal"].value,
                        "confidence": score_result["confidence"],
                        "explanation": score_result["explanation"],
                        "entry_price": signal.entry_price,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "position_pct": signal.position_pct,
                    }
                )
            except Exception:
                logger.warning("Analysis failed for %s", code, exc_info=True)
                continue

        results.sort(key=lambda x: x["score"], reverse=True)
        return Response(
            {
                "style": style,
                "count": len(results[:limit]),
                "results": results[:limit],
            }
        )


class AIReportView(APIView):
    """POST /api/quant/ai-report/ - Generate AI analysis report.

    Request body: { "stock_code": "000001" }
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = StockCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stock_code = serializer.validated_data["stock_code"]

        from .analyzers import AIAnalyzer, MultiFactorScorer

        # Get analysis data first
        scorer = MultiFactorScorer()
        score_result = scorer.score(stock_code)

        # Generate AI report
        ai_analyzer = AIAnalyzer()
        report = ai_analyzer.generate_report(
            stock_code,
            {
                "score": score_result["final_score"],
                "signal": score_result["signal"].value,
                "confidence": score_result["confidence"],
                "component_scores": score_result["component_scores"],
            },
        )

        return Response(
            {
                "stock_code": stock_code,
                "report": report,
                "analysis_summary": {
                    "score": score_result["final_score"],
                    "signal": score_result["signal"].value,
                    "confidence": score_result["confidence"],
                },
            }
        )


class FactorWeightConfigView(APIView):
    """GET/PUT /api/quant/config/weights/ - Factor weight configuration.

    GET: Return current weights for all styles.
    PUT: Update weights for a specific style.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        from .analyzers import MultiFactorScorer, TradingStyle

        weights = {}
        for style in TradingStyle:
            weights[style.value] = MultiFactorScorer.STYLE_WEIGHTS[style]
        return Response(weights)

    def put(self, request):
        serializer = FactorWeightSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        style = serializer.validated_data["style"]
        weights = serializer.validated_data["weights"]

        # Validate weights sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            return Response(
                {"error": f"Weights must sum to 1.0, got {total}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "style": style,
                "weights": weights,
                "message": "Weight configuration validated but persistence not yet implemented",
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class TaskMonitorView(APIView):
    """GET /api/quant/tasks/ - Monitor Celery task status.

    Returns status of recent Celery tasks and Beat schedule.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        from django.conf import settings

        # Return Beat schedule info
        schedule = {}
        for name, config in settings.CELERY_BEAT_SCHEDULE.items():
            schedule[name] = {
                "task": config["task"],
                "schedule": str(config["schedule"]),
            }
            if "kwargs" in config:
                schedule[name]["kwargs"] = config["kwargs"]

        return Response(
            {
                "beat_schedule": schedule,
                "schedule_count": len(schedule),
            }
        )

    def post(self, request):
        """Trigger a task manually."""
        task_name = request.data.get("task")
        kwargs = request.data.get("kwargs", {})

        task_map = {
            "sync_stock_list": "quant.sync_stock_list",
            "sync_daily_kline": "quant.sync_daily_kline",
            "sync_money_flow": "quant.sync_money_flow",
            "sync_margin_data": "quant.sync_margin_data",
            "sync_financial_reports": "quant.sync_financial_reports",
            "sync_news": "quant.sync_news",
            "validate_data": "quant.validate_data",
            "run_analysis_pipeline": "quant.run_analysis_pipeline",
        }

        if task_name not in task_map:
            return Response(
                {
                    "error": f"Unknown task: {task_name}",
                    "available": list(task_map.keys()),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from celery import current_app

        result = current_app.send_task(task_map[task_name], kwargs=kwargs)

        return Response(
            {
                "task_name": task_name,
                "task_id": result.id,
                "status": "PENDING",
            }
        )
