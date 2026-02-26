"""DRF views for paper trading simulator."""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Portfolio
from .engine import InsufficientFundsError, InsufficientSharesError, SimulatorEngine
from .serializers import (
    PerformanceMetricSerializer,
    PortfolioCreateSerializer,
    PortfolioSerializer,
    PositionSerializer,
    TradeExecuteSerializer,
    TradeSerializer,
)


class PortfolioViewSet(viewsets.ModelViewSet):
    """CRUD for portfolios + execute trade + performance actions.

    Endpoints:
    - GET    /api/quant/portfolios/                      - List user's portfolios
    - POST   /api/quant/portfolios/                      - Create portfolio
    - GET    /api/quant/portfolios/{id}/                  - Portfolio detail with summary
    - PUT    /api/quant/portfolios/{id}/                  - Update portfolio
    - DELETE /api/quant/portfolios/{id}/                  - Delete portfolio
    - POST   /api/quant/portfolios/{id}/trade/            - Execute a trade
    - GET    /api/quant/portfolios/{id}/positions/         - List positions
    - GET    /api/quant/portfolios/{id}/trades/            - List trades
    - GET    /api/quant/portfolios/{id}/performance/       - List performance metrics
    - POST   /api/quant/portfolios/{id}/calculate-performance/ - Calculate today's perf
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return PortfolioCreateSerializer
        return PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """Return portfolio with full summary from engine."""
        portfolio = self.get_object()
        engine = SimulatorEngine(portfolio)
        summary = engine.get_portfolio_summary()
        return Response(summary)

    @action(detail=True, methods=["post"])
    def trade(self, request, pk=None):
        """Execute a buy or sell trade."""
        portfolio = self.get_object()
        serializer = TradeExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine = SimulatorEngine(portfolio)
        data = serializer.validated_data

        try:
            if data["trade_type"] == "BUY":
                trade_obj = engine.buy(
                    stock_code=data["stock_code"],
                    shares=data["shares"],
                    price=data["price"],
                    reason=data.get("reason", ""),
                )
            else:
                trade_obj = engine.sell(
                    stock_code=data["stock_code"],
                    shares=data["shares"],
                    price=data["price"],
                    reason=data.get("reason", ""),
                )
        except InsufficientFundsError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except InsufficientSharesError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            TradeSerializer(trade_obj).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"])
    def positions(self, request, pk=None):
        """List positions for this portfolio."""
        portfolio = self.get_object()
        positions = portfolio.positions.select_related("stock").all()
        serializer = PositionSerializer(positions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def trades(self, request, pk=None):
        """List trades for this portfolio."""
        portfolio = self.get_object()
        trades = portfolio.trades.all()
        serializer = TradeSerializer(trades, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        """List performance metrics for this portfolio."""
        portfolio = self.get_object()
        metrics = portfolio.performance_metrics.all()
        serializer = PerformanceMetricSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="calculate-performance")
    def calculate_performance(self, request, pk=None):
        """Calculate today's performance metrics."""
        portfolio = self.get_object()
        engine = SimulatorEngine(portfolio)
        metric = engine.calculate_performance()
        return Response(PerformanceMetricSerializer(metric).data)
