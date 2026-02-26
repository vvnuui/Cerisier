"""Signal generator that converts multi-factor scores into actionable trading signals."""

from dataclasses import dataclass, field

from .types import Signal, TradingStyle


@dataclass
class TradingSignal:
    """Actionable trading signal."""

    stock_code: str
    signal: Signal
    score: float  # 0-100
    confidence: float  # 0-1
    style: TradingStyle

    # Price levels
    entry_price: float
    stop_loss: float
    take_profit: float

    # Position sizing
    position_pct: float  # Suggested portfolio allocation % (0-100)
    risk_reward_ratio: float  # take_profit distance / stop_loss distance

    # Metadata
    explanation: str
    details: dict = field(default_factory=dict)


class SignalGenerator:
    """Generates actionable trading signals from multi-factor scores.

    Takes scorer results + recent price data to compute:
    - Entry price: current close (or adjusted for BUY/SELL)
    - Stop-loss: Based on ATR (Average True Range) * multiplier
    - Take-profit: Based on risk-reward ratio target
    - Position size: Based on score confidence and Kelly-like sizing
    """

    # ATR multiplier for stop-loss by style
    STOP_LOSS_ATR_MULT = {
        TradingStyle.ULTRA_SHORT: 1.5,
        TradingStyle.SWING: 2.5,
        TradingStyle.MID_LONG: 3.5,
    }

    # Target risk-reward ratio by style
    TARGET_RR = {
        TradingStyle.ULTRA_SHORT: 2.0,
        TradingStyle.SWING: 3.0,
        TradingStyle.MID_LONG: 4.0,
    }

    # Max position allocation % by style
    MAX_POSITION_PCT = {
        TradingStyle.ULTRA_SHORT: 10.0,
        TradingStyle.SWING: 15.0,
        TradingStyle.MID_LONG: 25.0,
    }

    def __init__(self, atr_period: int = 14):
        self.atr_period = atr_period

    def generate(self, stock_code: str, scorer_result: dict) -> TradingSignal:
        """Generate a trading signal from a scorer result.

        Args:
            stock_code: Stock code
            scorer_result: Dict from MultiFactorScorer.score()

        Returns:
            TradingSignal with computed price levels and position sizing.
        """
        signal = scorer_result["signal"]
        score = scorer_result["final_score"]
        confidence = scorer_result["confidence"]
        style = scorer_result["style"]

        # Get recent kline data for ATR calculation
        from ..models import KlineData

        klines = list(
            KlineData.objects.filter(stock_id=stock_code)
            .order_by("-date")[: max(self.atr_period + 1, 30)]
        )

        if not klines:
            return TradingSignal(
                stock_code=stock_code,
                signal=Signal.HOLD,
                score=score,
                confidence=0.0,
                style=style,
                entry_price=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                position_pct=0.0,
                risk_reward_ratio=0.0,
                explanation="No price data available for signal generation",
            )

        current_price = float(klines[0].close)
        atr = self._calculate_atr(klines)

        # Compute price levels
        entry_price = current_price
        stop_loss_mult = self.STOP_LOSS_ATR_MULT[style]
        target_rr = self.TARGET_RR[style]

        if signal == Signal.BUY:
            stop_loss = entry_price - atr * stop_loss_mult
            take_profit = entry_price + atr * stop_loss_mult * target_rr
        elif signal == Signal.SELL:
            stop_loss = entry_price + atr * stop_loss_mult
            take_profit = entry_price - atr * stop_loss_mult * target_rr
        else:  # HOLD
            stop_loss = entry_price - atr * stop_loss_mult
            take_profit = entry_price + atr * stop_loss_mult

        # Position sizing: confidence * score factor * max allocation
        max_pct = self.MAX_POSITION_PCT[style]
        score_factor = abs(score - 50) / 50  # 0 when neutral, 1 when extreme
        position_pct = round(max_pct * confidence * score_factor, 2)

        # Risk-reward ratio
        sl_distance = abs(entry_price - stop_loss)
        tp_distance = abs(take_profit - entry_price)
        risk_reward_ratio = (
            round(tp_distance / sl_distance, 2) if sl_distance > 0 else 0.0
        )

        # Round prices to 2 decimal places
        entry_price = round(entry_price, 2)
        stop_loss = round(stop_loss, 2)
        take_profit = round(take_profit, 2)

        explanation = self._build_explanation(
            signal, style, entry_price, stop_loss, take_profit, position_pct,
            risk_reward_ratio,
        )

        return TradingSignal(
            stock_code=stock_code,
            signal=signal,
            score=score,
            confidence=confidence,
            style=style,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_pct=position_pct,
            risk_reward_ratio=risk_reward_ratio,
            explanation=explanation,
            details={
                "atr": round(atr, 4),
                "current_price": current_price,
                "stop_loss_atr_mult": stop_loss_mult,
                "target_rr": target_rr,
            },
        )

    def _calculate_atr(self, klines: list) -> float:
        """Calculate Average True Range from kline data.

        Klines are ordered newest-first.
        """
        if len(klines) < 2:
            # Fallback: use high-low range of single candle
            return float(klines[0].high - klines[0].low)

        true_ranges = []
        # Reverse to process oldest-first
        sorted_klines = list(reversed(klines))
        for i in range(1, len(sorted_klines)):
            high = float(sorted_klines[i].high)
            low = float(sorted_klines[i].low)
            prev_close = float(sorted_klines[i - 1].close)
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        # Use the last atr_period values
        recent_trs = true_ranges[-self.atr_period :]
        return sum(recent_trs) / len(recent_trs) if recent_trs else 0.0

    @staticmethod
    def _build_explanation(
        signal, style, entry, sl, tp, position_pct, rr
    ) -> str:
        if signal == Signal.BUY:
            return (
                f"BUY signal ({style.value}): "
                f"Entry {entry:.2f}, SL {sl:.2f}, TP {tp:.2f}, "
                f"Position {position_pct:.1f}%, RR {rr:.1f}:1"
            )
        elif signal == Signal.SELL:
            return (
                f"SELL signal ({style.value}): "
                f"Entry {entry:.2f}, SL {sl:.2f}, TP {tp:.2f}, "
                f"Position {position_pct:.1f}%, RR {rr:.1f}:1"
            )
        else:
            return f"HOLD signal ({style.value}): No trading action recommended"
