"""DRF serializers for quant data and analysis APIs."""

from rest_framework import serializers

from .models import FinancialReport, KlineData, MoneyFlow, NewsArticle, StockBasic


class StockBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockBasic
        fields = [
            "code",
            "name",
            "industry",
            "sector",
            "market",
            "list_date",
            "is_active",
        ]


class KlineDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = KlineData
        fields = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "turnover",
            "change_pct",
        ]


class MoneyFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoneyFlow
        fields = ["date", "main_net", "huge_net", "big_net", "mid_net", "small_net"]


class FinancialReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialReport
        fields = [
            "period",
            "pe_ratio",
            "pb_ratio",
            "roe",
            "revenue",
            "net_profit",
            "gross_margin",
            "debt_ratio",
            "report_date",
        ]


class NewsArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsArticle
        fields = ["id", "title", "source", "url", "sentiment_score", "published_at"]


class StockAnalysisRequestSerializer(serializers.Serializer):
    """Request serializer for stock analysis."""

    stock_code = serializers.CharField(max_length=10)
    style = serializers.ChoiceField(
        choices=["ultra_short", "swing", "mid_long"],
        default="swing",
    )


class RecommendationFilterSerializer(serializers.Serializer):
    """Query params for recommendations endpoint."""

    style = serializers.ChoiceField(
        choices=["ultra_short", "swing", "mid_long"],
        default="swing",
        required=False,
    )
    signal = serializers.ChoiceField(
        choices=["BUY", "SELL", "HOLD"],
        required=False,
    )
    min_score = serializers.FloatField(required=False, default=0)
    limit = serializers.IntegerField(
        required=False, default=20, min_value=1, max_value=100
    )


class FactorWeightSerializer(serializers.Serializer):
    """Serializer for factor weight configuration."""

    style = serializers.ChoiceField(choices=["ultra_short", "swing", "mid_long"])
    weights = serializers.DictField(
        child=serializers.FloatField(min_value=0, max_value=1)
    )
