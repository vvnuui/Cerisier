"""AI service for stock analysis with provider switching and budget tracking."""

import json
import logging
from datetime import date

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for AI service errors."""

    pass


class BudgetExceededError(AIServiceError):
    """Raised when daily API budget is exceeded."""

    pass


class AIService:
    """AI-powered stock analysis with provider switching.

    Supports two providers:
    - deepseek: Cost-effective for bulk analysis (default)
    - chatgpt: Premium quality for detailed reports

    Features:
    - Provider switching via constructor or per-call
    - Daily API budget tracking (stored in Django cache)
    - Graceful fallback on API errors
    - JSON response parsing with validation
    """

    # Provider configurations
    PROVIDERS = {
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "api_key_setting": "DEEPSEEK_API_KEY",
        },
        "chatgpt": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key_setting": "OPENAI_API_KEY",
        },
    }

    # Default daily budget in USD
    DEFAULT_DAILY_BUDGET = 5.0

    # Approximate cost per 1K tokens (for budget estimation)
    COST_PER_1K_TOKENS = {
        "deepseek": 0.001,
        "chatgpt": 0.01,
    }

    def __init__(self, provider: str = "deepseek"):
        """Initialize AIService.

        Args:
            provider: "deepseek" or "chatgpt"
        """
        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Choose from: {list(self.PROVIDERS.keys())}"
            )

        self.provider = provider
        self._client = None  # Lazy initialization

    @property
    def client(self):
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise AIServiceError(
                    "openai package not installed. Run: pip install openai"
                )

            provider_config = self.PROVIDERS[self.provider]
            api_key = getattr(settings, provider_config["api_key_setting"], None)
            if not api_key:
                # Try environment variable via decouple
                from decouple import config as decouple_config

                api_key = decouple_config(
                    provider_config["api_key_setting"], default=""
                )

            if not api_key:
                raise AIServiceError(
                    f"API key not configured for {self.provider}. "
                    f"Set {provider_config['api_key_setting']} in environment."
                )

            self._client = OpenAI(
                api_key=api_key,
                base_url=provider_config["base_url"],
            )
        return self._client

    # ------------------------------------------------------------------
    # Budget tracking
    # ------------------------------------------------------------------

    def _get_budget_key(self) -> str:
        return f"ai_budget:{self.provider}:{date.today().isoformat()}"

    def get_daily_spend(self) -> float:
        """Get today's estimated spend for the current provider."""
        return cache.get(self._get_budget_key(), 0.0)

    def _record_usage(self, total_tokens: int):
        """Record token usage for budget tracking."""
        cost_per_1k = self.COST_PER_1K_TOKENS.get(self.provider, 0.01)
        estimated_cost = (total_tokens / 1000) * cost_per_1k

        key = self._get_budget_key()
        current = cache.get(key, 0.0)
        cache.set(key, current + estimated_cost, timeout=86400)  # 24h TTL

    def _check_budget(self):
        """Check if daily budget has been exceeded."""
        daily_budget = getattr(
            settings, "AI_DAILY_BUDGET", self.DEFAULT_DAILY_BUDGET
        )
        if self.get_daily_spend() >= daily_budget:
            raise BudgetExceededError(
                f"Daily AI budget exceeded for {self.provider}: "
                f"${self.get_daily_spend():.2f} / ${daily_budget:.2f}"
            )

    # ------------------------------------------------------------------
    # Core API call
    # ------------------------------------------------------------------

    def _call_api(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 2000
    ) -> dict:
        """Make an API call and parse JSON response.

        Args:
            system_prompt: System message
            user_prompt: User message
            max_tokens: Maximum response tokens

        Returns:
            Parsed JSON dict from the response

        Raises:
            AIServiceError: On API or parsing errors
            BudgetExceededError: If daily budget exceeded
        """
        self._check_budget()

        provider_config = self.PROVIDERS[self.provider]

        try:
            response = self.client.chat.completions.create(
                model=provider_config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,  # Low temperature for analytical consistency
                response_format={"type": "json_object"},
            )

            # Record usage
            if response.usage:
                self._record_usage(response.usage.total_tokens)

            # Parse JSON response
            content = response.choices[0].message.content
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            raise AIServiceError(
                f"Invalid JSON response from {self.provider}: {e}"
            )
        except BudgetExceededError:
            raise
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"AI API call failed ({self.provider}): {e}")
            raise AIServiceError(f"API call failed: {e}")

    # ------------------------------------------------------------------
    # Public analysis methods
    # ------------------------------------------------------------------

    def analyze_news(
        self, stock_code: str, stock_name: str, articles: list[dict]
    ) -> dict:
        """Analyze news articles for sentiment and impact.

        Args:
            stock_code: Stock code
            stock_name: Stock name
            articles: List of dicts with 'title' and optional 'content'

        Returns:
            Dict with 'articles' key containing analyzed results
        """
        from .prompts import NEWS_ANALYSIS_PROMPT, SYSTEM_PROMPT_BASE

        system = SYSTEM_PROMPT_BASE
        user = NEWS_ANALYSIS_PROMPT.format(
            stock_code=stock_code, stock_name=stock_name
        )

        # Add article data
        article_text = "\n\n".join(
            f"Title: {a['title']}\nContent: {a.get('content', 'N/A')}"
            for a in articles[:10]  # Limit to 10 articles
        )
        user += f"\n\nArticles:\n{article_text}"

        return self._call_api(system, user)

    def analyze_financial(
        self, stock_code: str, stock_name: str, financial_data: dict
    ) -> dict:
        """Analyze financial data with AI.

        Args:
            stock_code: Stock code
            stock_name: Stock name
            financial_data: Dict with financial metrics

        Returns:
            Dict with score, strengths, weaknesses, recommendation
        """
        from .prompts import FINANCIAL_ANALYSIS_PROMPT, SYSTEM_PROMPT_BASE

        system = SYSTEM_PROMPT_BASE
        user = FINANCIAL_ANALYSIS_PROMPT.format(
            stock_code=stock_code,
            stock_name=stock_name,
            financial_data=json.dumps(financial_data, ensure_ascii=False),
        )

        return self._call_api(system, user)

    def score_factors(
        self, stock_code: str, stock_name: str, factor_data: dict
    ) -> dict:
        """AI-assisted factor scoring adjustment.

        Args:
            stock_code: Stock code
            stock_name: Stock name
            factor_data: Dict with multi-factor analysis results

        Returns:
            Dict with adjusted_score, reasoning, risk_factors, catalysts
        """
        from .prompts import FACTOR_SCORING_PROMPT, SYSTEM_PROMPT_BASE

        system = SYSTEM_PROMPT_BASE
        user = FACTOR_SCORING_PROMPT.format(
            stock_code=stock_code,
            stock_name=stock_name,
            factor_data=json.dumps(factor_data, ensure_ascii=False),
        )

        return self._call_api(system, user)

    def generate_report(
        self, stock_code: str, stock_name: str, analysis_data: dict
    ) -> dict:
        """Generate a comprehensive analysis report.

        Args:
            stock_code: Stock code
            stock_name: Stock name
            analysis_data: Dict with full analysis results

        Returns:
            Dict with summary, technical, fundamental, risks, recommendation
        """
        from .prompts import REPORT_GENERATION_PROMPT, SYSTEM_PROMPT_BASE

        system = SYSTEM_PROMPT_BASE
        user = REPORT_GENERATION_PROMPT.format(
            stock_code=stock_code,
            stock_name=stock_name,
            analysis_data=json.dumps(analysis_data, ensure_ascii=False),
        )

        return self._call_api(system, user, max_tokens=4000)
