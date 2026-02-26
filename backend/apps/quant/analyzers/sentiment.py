"""Sentiment analysis: average sentiment, trend, and news volume signal."""

import logging
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .base import AnalyzerBase
from .types import AnalysisResult, Signal
from ..models import NewsArticle

logger = logging.getLogger(__name__)


class SentimentAnalyzer(AnalyzerBase):
    """News sentiment analysis from NewsArticle data.

    Scoring components (each 0-100):
      - avg_sentiment  (40%): Average sentiment_score of recent articles
      - sentiment_trend(30%): Trend direction of sentiment over time
      - volume_signal  (30%): News volume combined with sentiment direction

    Final score is a weighted average clamped to 0-100.
    Score >= 70 -> BUY, <= 30 -> SELL, else HOLD.
    """

    name = "sentiment"
    description = "News sentiment analysis (average sentiment, trend, volume)"

    WEIGHTS = {
        "avg_sentiment": 0.40,
        "sentiment_trend": 0.30,
        "volume_signal": 0.30,
    }

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        cutoff = timezone.now() - timedelta(days=self.lookback_days)
        articles = list(
            NewsArticle.objects.filter(
                stock_id=stock_code,
                published_at__gte=cutoff,
                sentiment_score__isnull=False,
            ).order_by("published_at")
        )

        if len(articles) < 3:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient news articles for sentiment analysis",
            )

        component_scores = {
            "avg_sentiment": self._score_avg_sentiment(articles),
            "sentiment_trend": self._score_sentiment_trend(articles),
            "volume_signal": self._score_volume_signal(articles),
        }

        final_score = sum(
            component_scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS
        )
        final_score = round(max(0.0, min(100.0, final_score)), 2)

        if final_score >= 70:
            signal = Signal.BUY
        elif final_score <= 30:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        confidence = self._compute_confidence(articles)
        explanation = self._build_explanation(component_scores, signal)

        return AnalysisResult(
            score=final_score,
            signal=signal,
            confidence=confidence,
            explanation=explanation,
            details={"component_scores": component_scores},
        )

    # ------------------------------------------------------------------
    # Average sentiment (40%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_avg_sentiment(articles: list) -> float:
        """Map average sentiment_score to 0-100.

        sentiment_score is assumed to be in range [-1, 1] where:
        -1 = very negative, 0 = neutral, +1 = very positive.
        """
        scores = [float(a.sentiment_score) for a in articles]
        avg = sum(scores) / len(scores)

        # Map [-1, 1] to [0, 100].
        score = (avg + 1) / 2 * 100
        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Sentiment trend (30%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_sentiment_trend(articles: list) -> float:
        """Compare first-half vs second-half average sentiment."""
        scores = [float(a.sentiment_score) for a in articles]
        if len(scores) < 2:
            return 50.0

        mid = len(scores) // 2
        first_half = scores[:mid] if mid > 0 else scores[:1]
        second_half = scores[mid:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        diff = avg_second - avg_first

        score = 50.0
        # Improving sentiment = bullish.
        if diff > 0.3:
            score += 30
        elif diff > 0.1:
            score += 20
        elif diff > 0:
            score += 10
        elif diff > -0.1:
            score -= 10
        elif diff > -0.3:
            score -= 20
        else:
            score -= 30

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Volume signal (30%)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_volume_signal(articles: list) -> float:
        """High news volume combined with sentiment direction.

        Many articles + positive sentiment = strong bullish signal.
        Many articles + negative sentiment = strong bearish signal.
        """
        count = len(articles)
        avg_sentiment = sum(float(a.sentiment_score) for a in articles) / count

        score = 50.0

        # Volume component: more articles = more attention.
        if count >= 20:
            volume_boost = 20
        elif count >= 10:
            volume_boost = 15
        elif count >= 5:
            volume_boost = 10
        else:
            volume_boost = 5

        # Apply volume boost in the direction of sentiment.
        if avg_sentiment > 0.1:
            score += volume_boost
        elif avg_sentiment < -0.1:
            score -= volume_boost

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_confidence(articles: list) -> float:
        """Confidence based on number of articles with sentiment scores."""
        count = len(articles)
        if count >= 20:
            return 0.9
        elif count >= 10:
            return 0.7
        elif count >= 5:
            return 0.5
        elif count >= 3:
            return 0.3
        return 0.0

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_explanation(scores: dict, signal: Signal) -> str:
        parts = []
        for name, s in sorted(
            scores.items(), key=lambda x: abs(x[1] - 50), reverse=True
        ):
            if s >= 65:
                parts.append(f"{name} bullish ({s:.0f})")
            elif s <= 35:
                parts.append(f"{name} bearish ({s:.0f})")

        if signal == Signal.BUY:
            prefix = "Bullish sentiment"
        elif signal == Signal.SELL:
            prefix = "Bearish sentiment"
        else:
            prefix = "Mixed sentiment"

        detail = "; ".join(parts[:3]) if parts else "neutral news sentiment"
        return f"{prefix}: {detail}"
