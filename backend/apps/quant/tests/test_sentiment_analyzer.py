"""Tests for SentimentAnalyzer (average sentiment, trend, volume signal)."""

import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.quant.analyzers.sentiment import SentimentAnalyzer
from apps.quant.analyzers.types import AnalysisResult, Signal
from apps.quant.models import NewsArticle, StockBasic

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def stock(db):
    return StockBasic.objects.create(
        code="000001",
        name="平安银行",
        industry="银行",
        sector="金融",
        market="SZ",
        list_date=datetime.date(1991, 4, 3),
        is_active=True,
    )


def create_positive_articles(stock, count=10):
    """Create articles with positive sentiment scores."""
    articles = []
    now = timezone.now()
    for i in range(count):
        articles.append(
            NewsArticle(
                stock=stock,
                title=f"Positive news {i}",
                content="Great earnings report",
                source="TestSource",
                sentiment_score=Decimal(str(0.6 + i * 0.02)),
                published_at=now - timedelta(days=count - i),
            )
        )
    NewsArticle.objects.bulk_create(articles)
    return articles


def create_negative_articles(stock, count=10):
    """Create articles with negative sentiment scores."""
    articles = []
    now = timezone.now()
    for i in range(count):
        articles.append(
            NewsArticle(
                stock=stock,
                title=f"Negative news {i}",
                content="Poor performance warning",
                source="TestSource",
                sentiment_score=Decimal(str(-0.6 - i * 0.02)),
                published_at=now - timedelta(days=count - i),
            )
        )
    NewsArticle.objects.bulk_create(articles)
    return articles


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSentimentAnalyzerName:
    def test_name(self):
        """Verify the analyzer name is 'sentiment'."""
        analyzer = SentimentAnalyzer()
        assert analyzer.name == "sentiment"


@pytest.mark.django_db
class TestSentimentBullish:
    def test_bullish_score(self, stock):
        """Positive sentiment articles should yield a bullish score > 55."""
        create_positive_articles(stock, count=10)
        analyzer = SentimentAnalyzer(lookback_days=30)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score > 55, (
            f"Expected bullish score > 55, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.SELL


@pytest.mark.django_db
class TestSentimentBearish:
    def test_bearish_score(self, stock):
        """Negative sentiment articles should yield a bearish score < 45."""
        create_negative_articles(stock, count=10)
        analyzer = SentimentAnalyzer(lookback_days=30)
        result = analyzer.analyze(stock.code)

        assert isinstance(result, AnalysisResult)
        assert result.score < 45, (
            f"Expected bearish score < 45, got {result.score}. "
            f"Component scores: {result.details.get('component_scores')}"
        )
        assert result.signal != Signal.BUY


@pytest.mark.django_db
class TestSentimentInsufficientData:
    def test_insufficient_data(self, stock):
        """Only 2 articles should return HOLD with confidence 0."""
        now = timezone.now()
        for i in range(2):
            NewsArticle.objects.create(
                stock=stock,
                title=f"News {i}",
                content="Some content",
                source="TestSource",
                sentiment_score=Decimal("0.5"),
                published_at=now - timedelta(days=i),
            )

        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0
        assert result.score == 50.0


@pytest.mark.django_db
class TestSentimentNullScoresExcluded:
    def test_null_sentiment_scores_excluded(self, stock):
        """Articles with null sentiment_score should not be counted."""
        now = timezone.now()
        # 2 articles with sentiment, 5 with null.
        for i in range(2):
            NewsArticle.objects.create(
                stock=stock,
                title=f"Scored news {i}",
                content="Content",
                source="TestSource",
                sentiment_score=Decimal("0.5"),
                published_at=now - timedelta(days=i),
            )
        for i in range(5):
            NewsArticle.objects.create(
                stock=stock,
                title=f"Unscored news {i}",
                content="Content",
                source="TestSource",
                sentiment_score=None,
                published_at=now - timedelta(days=i + 2),
            )

        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(stock.code)

        # Only 2 scored articles -> insufficient (< 3).
        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0


@pytest.mark.django_db
class TestSentimentComponentScores:
    def test_component_scores_in_details(self, stock):
        """Details should contain component_scores dict with all 3 keys."""
        create_positive_articles(stock, count=5)
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(stock.code)

        assert "component_scores" in result.details
        scores = result.details["component_scores"]
        expected_keys = {"avg_sentiment", "sentiment_trend", "volume_signal"}
        assert set(scores.keys()) == expected_keys

        for key, val in scores.items():
            assert 0.0 <= val <= 100.0, f"{key} score {val} out of range"


@pytest.mark.django_db
class TestSentimentConfidence:
    def test_confidence_many_articles(self, stock):
        """10 articles should yield confidence >= 0.5."""
        create_positive_articles(stock, count=10)
        analyzer = SentimentAnalyzer(lookback_days=30)
        result = analyzer.analyze(stock.code)

        assert result.confidence >= 0.5

    def test_confidence_few_articles(self, stock):
        """3 articles should yield confidence 0.3."""
        now = timezone.now()
        for i in range(3):
            NewsArticle.objects.create(
                stock=stock,
                title=f"News {i}",
                content="Content",
                source="TestSource",
                sentiment_score=Decimal("0.5"),
                published_at=now - timedelta(days=i),
            )

        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(stock.code)

        assert result.confidence == 0.3


@pytest.mark.django_db
class TestSentimentSafeAnalyze:
    def test_safe_analyze_missing_stock(self):
        """safe_analyze for a non-existent stock code returns HOLD."""
        analyzer = SentimentAnalyzer()
        result = analyzer.safe_analyze("DOESNOTEXIST")

        assert isinstance(result, AnalysisResult)
        assert result.signal == Signal.HOLD
        assert result.confidence == 0.0


@pytest.mark.django_db
class TestSentimentTrend:
    def test_improving_sentiment_trend(self, stock):
        """Articles that improve in sentiment over time should score trend > 50."""
        now = timezone.now()
        articles = []
        for i in range(10):
            articles.append(
                NewsArticle(
                    stock=stock,
                    title=f"News {i}",
                    content="Content",
                    source="TestSource",
                    sentiment_score=Decimal(str(-0.3 + i * 0.1)),
                    published_at=now - timedelta(days=10 - i),
                )
            )
        NewsArticle.objects.bulk_create(articles)

        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(stock.code)
        trend_score = result.details["component_scores"]["sentiment_trend"]
        assert trend_score > 50, f"Expected improving trend > 50, got {trend_score}"
