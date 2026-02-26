from abc import ABC, abstractmethod
import logging

from .types import AnalysisResult, Signal

logger = logging.getLogger(__name__)


class AnalyzerBase(ABC):
    """Base class for all stock analyzers."""

    name: str = "base"  # Override in subclass
    description: str = ""

    @abstractmethod
    def analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        """Analyze a stock and return a scored result.

        Args:
            stock_code: The stock code (e.g., "000001")
            **kwargs: Additional parameters

        Returns:
            AnalysisResult with score, signal, confidence, explanation
        """

    def safe_analyze(self, stock_code: str, **kwargs) -> AnalysisResult:
        """Wrapper that catches exceptions and returns a neutral result."""
        try:
            return self.analyze(stock_code, **kwargs)
        except Exception as e:
            logger.exception(f"{self.name} analyzer failed for {stock_code}: {e}")
            return AnalysisResult(
                score=50.0,
                signal=Signal.HOLD,
                confidence=0.0,
                explanation=f"Analysis failed: {str(e)}",
                details={"error": str(e)},
            )
