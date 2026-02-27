import logging

import numpy as np
import pandas as pd
from decimal import Decimal

from .base import AnalyzerBase
from .types import AnalysisResult, Signal
from ..models import KlineData

logger = logging.getLogger(__name__)


class TechnicalAnalyzer(AnalyzerBase):
    """Technical indicators analysis (MA, MACD, KDJ, BOLL, RSI, Volume).

    Computes six indicator sub-scores, combines them with fixed weights,
    and produces a 0-100 score that maps to BUY / SELL / HOLD.
    """

    name = "technical"
    description = "Technical indicators analysis (MA, MACD, KDJ, BOLL, RSI, Volume)"

    WEIGHTS = {
        "ma": 0.20,
        "macd": 0.20,
        "kdj": 0.15,
        "rsi": 0.15,
        "boll": 0.15,
        "volume": 0.15,
    }

    def __init__(self, lookback_days: int = 120):
        self.lookback_days = lookback_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        """Analyze a stock's technical indicators and return a scored result.

        Args:
            stock_code: The stock code (primary key of StockBasic).
            **kwargs: Ignored for now.

        Returns:
            AnalysisResult with score, signal, confidence, explanation, and
            per-indicator scores in ``details["indicator_scores"]``.
        """
        klines = KlineData.objects.filter(
            stock_id=stock_code
        ).order_by("date")[: self.lookback_days]

        if len(klines) < 30:
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation="Insufficient data for technical analysis",
            )

        df = self._to_dataframe(klines)

        # Calculate each indicator sub-score (0-100).
        scores = {
            "ma": self._analyze_ma(df),
            "macd": self._analyze_macd(df),
            "kdj": self._analyze_kdj(df),
            "boll": self._analyze_boll(df),
            "rsi": self._analyze_rsi(df),
            "volume": self._analyze_volume(df),
        }

        # Weighted combination.
        final_score = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        final_score = max(0.0, min(100.0, final_score))

        # Signal from score.
        if final_score >= 70:
            signal = Signal.BUY
        elif final_score <= 30:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        # Confidence: proportion of indicators that agree on direction.
        bullish_count = sum(1 for s in scores.values() if s >= 60)
        bearish_count = sum(1 for s in scores.values() if s <= 40)
        agreement = max(bullish_count, bearish_count) / len(scores)
        confidence = min(1.0, agreement * 1.2)

        explanation = self._build_explanation(scores, signal)

        return AnalysisResult(
            score=round(final_score, 2),
            signal=signal,
            confidence=round(confidence, 2),
            explanation=explanation,
            details={"indicator_scores": scores},
        )

    # ------------------------------------------------------------------
    # DataFrame conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dataframe(klines) -> pd.DataFrame:
        """Convert a QuerySet (or list) of KlineData into a pandas DataFrame."""
        data = []
        for k in klines:
            data.append(
                {
                    "date": k.date,
                    "open": float(k.open),
                    "high": float(k.high),
                    "low": float(k.low),
                    "close": float(k.close),
                    "volume": k.volume,
                    "amount": float(k.amount),
                }
            )
        df = pd.DataFrame(data)
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    # ------------------------------------------------------------------
    # Indicator sub-scores (each returns 0-100)
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_ma(df: pd.DataFrame) -> float:
        """MA analysis: price vs moving averages alignment.

        Awards points when the current close is above each MA and when the
        short-term MAs are stacked above the long-term ones (bullish alignment).
        """
        close = df["close"]
        current = close.iloc[-1]

        score = 50.0
        for period in [5, 10, 20, 60]:
            if len(close) >= period:
                ma = close.rolling(period).mean().iloc[-1]
                if current > ma:
                    score += 8  # above MA is bullish
                else:
                    score -= 8

        # Check MA alignment (MA5 > MA10 > MA20 = strong bull).
        if len(close) >= 20:
            ma5 = close.rolling(5).mean().iloc[-1]
            ma10 = close.rolling(10).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            if ma5 > ma10 > ma20:
                score += 10  # perfect bullish alignment
            elif ma5 < ma10 < ma20:
                score -= 10  # perfect bearish alignment

        return max(0.0, min(100.0, score))

    @staticmethod
    def _analyze_macd(df: pd.DataFrame) -> float:
        """MACD analysis (DIF / DEA / histogram).

        Checks: DIF vs DEA, histogram direction, golden/death cross,
        and the position of DIF relative to zero (trend context).
        """
        close = df["close"]
        if len(close) < 26:
            return 50.0

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_hist = (dif - dea) * 2

        score = 50.0

        # DIF above zero = overall uptrend context; below zero = downtrend.
        if dif.iloc[-1] > 0:
            score += 10
        else:
            score -= 10

        # DIF above DEA = bullish momentum.
        if dif.iloc[-1] > dea.iloc[-1]:
            score += 10
        else:
            score -= 10

        # MACD histogram positive and increasing.
        if macd_hist.iloc[-1] > 0:
            score += 5
            if len(macd_hist) >= 2 and macd_hist.iloc[-1] > macd_hist.iloc[-2]:
                score += 5  # increasing momentum
        else:
            score -= 5

        # Golden cross (DIF crosses above DEA).
        if len(dif) >= 2:
            if dif.iloc[-2] <= dea.iloc[-2] and dif.iloc[-1] > dea.iloc[-1]:
                score += 15  # golden cross
            elif dif.iloc[-2] >= dea.iloc[-2] and dif.iloc[-1] < dea.iloc[-1]:
                score -= 15  # death cross

        return max(0.0, min(100.0, score))

    @staticmethod
    def _analyze_kdj(df: pd.DataFrame) -> float:
        """KDJ analysis (K, D, J values).

        Checks: oversold/overbought zones, golden/death cross, J extremes.
        Uses duration in extreme zones to distinguish between contrarian
        bounce opportunities and sustained-trend confirmations.
        """
        if len(df) < 9:
            return 50.0

        low_min = df["low"].rolling(9).min()
        high_max = df["high"].rolling(9).max()

        rsv = (df["close"] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)

        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d

        score = 50.0
        k_val, d_val, j_val = k.iloc[-1], d.iloc[-1], j.iloc[-1]

        # Check how long K has been in extreme zones (last 10 bars).
        recent_k = k.iloc[-10:] if len(k) >= 10 else k
        pct_below_20 = (recent_k < 20).sum() / len(recent_k)
        pct_above_80 = (recent_k > 80).sum() / len(recent_k)

        # Overbought / oversold with trend duration check.
        if k_val < 20 and d_val < 20:
            if pct_below_20 > 0.6:
                score -= 10  # prolonged oversold = bearish trend
            else:
                score += 15  # fresh oversold = buy opportunity
        elif k_val > 80 and d_val > 80:
            if pct_above_80 > 0.6:
                score += 5  # prolonged overbought = strong uptrend
            else:
                score -= 15  # fresh overbought = sell signal

        # Golden cross.
        if len(k) >= 2:
            if k.iloc[-2] <= d.iloc[-2] and k.iloc[-1] > d.iloc[-1]:
                score += 15
            elif k.iloc[-2] >= d.iloc[-2] and k.iloc[-1] < d.iloc[-1]:
                score -= 15

        # J value extremes.
        if j_val < 0:
            if pct_below_20 > 0.6:
                score -= 5  # sustained bearish
            else:
                score += 10  # contrarian bounce
        elif j_val > 100:
            if pct_above_80 > 0.6:
                score += 5  # sustained bullish
            else:
                score -= 10  # contrarian pullback

        return max(0.0, min(100.0, score))

    @staticmethod
    def _analyze_boll(df: pd.DataFrame) -> float:
        """Bollinger Bands analysis.

        Checks the current price position relative to the upper/middle/lower
        bands, considering whether the price has been persistently below the
        middle band (bearish trend) or above it (bullish trend).
        """
        close = df["close"]
        if len(close) < 20:
            return 50.0

        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        upper = mid + 2 * std
        lower = mid - 2 * std

        current = close.iloc[-1]
        mid_val = mid.iloc[-1]
        upper_val = upper.iloc[-1]
        lower_val = lower.iloc[-1]

        # Check recent trend: how many of the last 10 closes are below mid.
        recent_close = close.iloc[-10:] if len(close) >= 10 else close
        recent_mid = mid.iloc[-10:] if len(mid) >= 10 else mid
        valid = recent_mid.notna()
        if valid.sum() > 0:
            pct_below_mid = (
                (recent_close[valid] < recent_mid[valid]).sum() / valid.sum()
            )
        else:
            pct_below_mid = 0.5

        score = 50.0
        band_width = upper_val - lower_val
        if band_width > 0:
            position = (current - lower_val) / band_width  # 0=lower, 1=upper

            if position < 0.2:
                if pct_below_mid > 0.7:
                    score -= 10  # persistently below mid = bearish trend
                else:
                    score += 15  # near lower band, potential bounce
            elif position > 0.8:
                if pct_below_mid < 0.3:
                    score += 5  # persistently above mid = bullish momentum
                else:
                    score -= 10  # near upper band, potential pullback

            if current > mid_val:
                score += 10
            else:
                score -= 10

        return max(0.0, min(100.0, score))

    @staticmethod
    def _analyze_rsi(df: pd.DataFrame) -> float:
        """RSI analysis (14-period).

        Uses a dual perspective: extreme RSI values can signal a contrarian
        bounce, but sustained extreme readings also confirm a strong trend.
        The scoring balances both views by checking whether RSI has been
        trending in the extreme zone.
        """
        close = df["close"]
        if len(close) < 14:
            return 50.0

        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)

        rsi_val = rsi.iloc[-1]
        score = 50.0

        # Check how long RSI has been in the extreme zone (last 10 bars).
        recent_rsi = rsi.iloc[-10:] if len(rsi) >= 10 else rsi
        pct_below_30 = (recent_rsi < 30).sum() / len(recent_rsi)
        pct_above_70 = (recent_rsi > 70).sum() / len(recent_rsi)

        if rsi_val < 20:
            if pct_below_30 > 0.7:
                # Prolonged oversold = strong downtrend confirmation.
                score -= 15
            else:
                # Just entered oversold = potential bounce.
                score += 15
        elif rsi_val < 30:
            if pct_below_30 > 0.7:
                score -= 10
            else:
                score += 10
        elif rsi_val < 40:
            score += 5
        elif rsi_val > 80:
            if pct_above_70 > 0.7:
                # Prolonged overbought = strong uptrend momentum.
                score += 10
            else:
                # Just entered overbought = potential pullback.
                score -= 15
        elif rsi_val > 70:
            if pct_above_70 > 0.7:
                score += 5
            else:
                score -= 10
        elif rsi_val > 60:
            score -= 5

        # RSI in healthy bullish zone (40-70).
        if 40 <= rsi_val <= 70:
            score += 5

        return max(0.0, min(100.0, score))

    @staticmethod
    def _analyze_volume(df: pd.DataFrame) -> float:
        """Volume analysis: volume-price relationship.

        Checks whether volume expansion confirms price direction.
        """
        if len(df) < 10:
            return 50.0

        volume = df["volume"]
        close = df["close"]

        avg_vol_5 = volume.rolling(5).mean().iloc[-1]
        avg_vol_20 = volume.rolling(min(20, len(volume))).mean().iloc[-1]

        score = 50.0

        # Volume expansion with price increase.
        price_change = close.iloc[-1] - close.iloc[-2] if len(close) >= 2 else 0
        vol_ratio = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1.0

        if price_change > 0 and vol_ratio > 1.2:
            score += 20  # price up + volume up = bullish
        elif price_change < 0 and vol_ratio > 1.2:
            score -= 15  # price down + volume up = bearish
        elif price_change > 0 and vol_ratio < 0.8:
            score -= 5  # price up on low volume = weak

        return max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Explanation builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_explanation(scores: dict, signal: Signal) -> str:
        """Build a human-readable explanation from indicator scores."""
        parts = []
        for name, s in sorted(
            scores.items(), key=lambda x: abs(x[1] - 50), reverse=True
        ):
            if s >= 65:
                parts.append(f"{name.upper()} bullish ({s:.0f})")
            elif s <= 35:
                parts.append(f"{name.upper()} bearish ({s:.0f})")

        if signal == Signal.BUY:
            prefix = "Bullish technical signals"
        elif signal == Signal.SELL:
            prefix = "Bearish technical signals"
        else:
            prefix = "Mixed technical signals"

        detail = "; ".join(parts[:3]) if parts else "neutral across indicators"
        return f"{prefix}: {detail}"
