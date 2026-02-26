"""DRF serializers for paper trading simulator."""

from rest_framework import serializers

from ..models import PerformanceMetric, Portfolio, Position, Trade


class PortfolioSerializer(serializers.ModelSerializer):
    total_value = serializers.SerializerMethodField()
    position_count = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "name",
            "initial_capital",
            "cash_balance",
            "is_active",
            "total_value",
            "position_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "cash_balance", "created_at", "updated_at"]

    def get_total_value(self, obj):
        positions = obj.positions.all()
        market_value = sum(p.market_value for p in positions)
        return float(obj.cash_balance + market_value)

    def get_position_count(self, obj):
        return obj.positions.count()


class PortfolioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = ["name", "initial_capital"]

    def create(self, validated_data):
        user = self.context["request"].user
        capital = validated_data.get("initial_capital", 1000000)
        return Portfolio.objects.create(
            user=user,
            cash_balance=capital,
            **validated_data,
        )


class PositionSerializer(serializers.ModelSerializer):
    stock_code = serializers.CharField(source="stock_id")
    stock_name = serializers.CharField(source="stock.name", read_only=True)
    market_value = serializers.SerializerMethodField()
    unrealized_pnl = serializers.SerializerMethodField()
    unrealized_pnl_pct = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            "id",
            "stock_code",
            "stock_name",
            "shares",
            "avg_cost",
            "current_price",
            "market_value",
            "unrealized_pnl",
            "unrealized_pnl_pct",
            "updated_at",
        ]

    def get_market_value(self, obj):
        return float(obj.market_value)

    def get_unrealized_pnl(self, obj):
        return float(obj.unrealized_pnl)

    def get_unrealized_pnl_pct(self, obj):
        return round(obj.unrealized_pnl_pct, 2)


class TradeSerializer(serializers.ModelSerializer):
    stock_code = serializers.CharField(source="stock_id")

    class Meta:
        model = Trade
        fields = [
            "id",
            "stock_code",
            "trade_type",
            "shares",
            "price",
            "amount",
            "commission",
            "reason",
            "executed_at",
        ]


class TradeExecuteSerializer(serializers.Serializer):
    """Serializer for executing a trade."""

    stock_code = serializers.CharField(max_length=10)
    trade_type = serializers.ChoiceField(choices=["BUY", "SELL"])
    shares = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=4)
    reason = serializers.CharField(max_length=200, required=False, default="")


class PerformanceMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceMetric
        fields = [
            "id",
            "date",
            "total_value",
            "daily_return",
            "cumulative_return",
            "max_drawdown",
            "sharpe_ratio",
            "win_rate",
        ]
