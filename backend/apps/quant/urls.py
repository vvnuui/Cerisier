from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .simulator.views import PortfolioViewSet
from .views import (
    AIReportView,
    FactorWeightConfigView,
    FinancialReportView,
    KlineDataView,
    MoneyFlowView,
    RecommendationsView,
    StockAnalysisView,
    StockDetailView,
    StockListView,
    StockNewsView,
    TaskMonitorView,
)

router = DefaultRouter()
router.register(r"quant/portfolios", PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path("", include(router.urls)),
    # Stock data endpoints
    path("quant/stocks/", StockListView.as_view(), name="stock-list"),
    path("quant/stocks/<str:code>/", StockDetailView.as_view(), name="stock-detail"),
    path(
        "quant/stocks/<str:code>/kline/",
        KlineDataView.as_view(),
        name="stock-kline",
    ),
    path(
        "quant/stocks/<str:code>/money-flow/",
        MoneyFlowView.as_view(),
        name="stock-money-flow",
    ),
    path(
        "quant/stocks/<str:code>/financials/",
        FinancialReportView.as_view(),
        name="stock-financials",
    ),
    path(
        "quant/stocks/<str:code>/news/",
        StockNewsView.as_view(),
        name="stock-news",
    ),
    # Analysis endpoints
    path("quant/analysis/", StockAnalysisView.as_view(), name="stock-analysis"),
    path(
        "quant/recommendations/",
        RecommendationsView.as_view(),
        name="recommendations",
    ),
    path("quant/ai-report/", AIReportView.as_view(), name="ai-report"),
    # Config endpoints
    path(
        "quant/config/weights/",
        FactorWeightConfigView.as_view(),
        name="factor-weights",
    ),
    # Task monitoring
    path("quant/tasks/", TaskMonitorView.as_view(), name="task-monitor"),
]
