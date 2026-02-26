from dataclasses import dataclass, field
from enum import Enum


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradingStyle(Enum):
    ULTRA_SHORT = "ultra_short"  # 超短线 (1-3 days)
    SWING = "swing"  # 波段 (1-4 weeks)
    MID_LONG = "mid_long"  # 中长线 (1-6 months)


@dataclass
class AnalysisResult:
    """Result from a single analyzer dimension."""

    score: float  # 0-100, higher = more bullish
    signal: Signal  # Primary signal
    confidence: float  # 0.0-1.0, reliability of analysis
    explanation: str  # Human-readable explanation
    details: dict = field(default_factory=dict)  # Extra data (indicator values, etc.)

    def __post_init__(self):
        if not 0 <= self.score <= 100:
            raise ValueError(f"Score must be 0-100, got {self.score}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")
