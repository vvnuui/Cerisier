"""Tests for AI service abstraction."""

import json

import pytest
from django.core.cache import cache
from unittest.mock import MagicMock, PropertyMock, patch

from apps.quant.ai.service import AIService, AIServiceError, BudgetExceededError


def _mock_completion(content_dict, total_tokens=500):
    """Create a mock OpenAI completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(content_dict)
    mock_response.usage.total_tokens = total_tokens
    return mock_response


class TestAIServiceInit:
    """Test AIService initialization and configuration."""

    def test_default_provider(self):
        """Default provider is 'deepseek'."""
        service = AIService()
        assert service.provider == "deepseek"

    def test_chatgpt_provider(self):
        """Can initialize with chatgpt provider."""
        service = AIService(provider="chatgpt")
        assert service.provider == "chatgpt"

    def test_invalid_provider_raises(self):
        """Raises ValueError for unknown provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            AIService(provider="invalid-provider")

    def test_providers_config(self):
        """Both providers have required config keys."""
        required_keys = {"base_url", "model", "api_key_setting"}
        for name, cfg in AIService.PROVIDERS.items():
            assert required_keys.issubset(
                cfg.keys()
            ), f"Provider {name} missing keys"

    def test_lazy_client_initialization(self):
        """Client is not created until first access."""
        service = AIService()
        assert service._client is None


class TestBudgetTracking:
    """Test daily budget tracking via Django cache."""

    def setup_method(self):
        cache.clear()

    def test_initial_spend_is_zero(self):
        """Daily spend starts at zero."""
        service = AIService()
        assert service.get_daily_spend() == 0.0

    def test_record_usage_updates_spend(self):
        """Recording token usage increases daily spend."""
        service = AIService()
        service._record_usage(1000)  # 1K tokens
        spend = service.get_daily_spend()
        assert spend > 0
        # deepseek cost: 1000 / 1000 * 0.001 = 0.001
        assert abs(spend - 0.001) < 1e-9

    def test_record_usage_accumulates(self):
        """Multiple usage recordings accumulate."""
        service = AIService()
        service._record_usage(1000)
        service._record_usage(2000)
        spend = service.get_daily_spend()
        # 1000/1000*0.001 + 2000/1000*0.001 = 0.003
        assert abs(spend - 0.003) < 1e-9

    def test_chatgpt_cost_higher(self):
        """ChatGPT has higher per-token cost than DeepSeek."""
        ds_service = AIService(provider="deepseek")
        gpt_service = AIService(provider="chatgpt")
        ds_service._record_usage(1000)
        gpt_service._record_usage(1000)
        assert gpt_service.get_daily_spend() > ds_service.get_daily_spend()

    def test_budget_exceeded_raises(self):
        """Raises BudgetExceededError when spend >= budget."""
        service = AIService()
        # Set spend to exceed default budget (5.0)
        key = service._get_budget_key()
        cache.set(key, 5.0, timeout=86400)

        with pytest.raises(BudgetExceededError, match="Daily AI budget exceeded"):
            service._check_budget()

    def test_budget_not_exceeded_passes(self):
        """No error when spend is below budget."""
        service = AIService()
        key = service._get_budget_key()
        cache.set(key, 1.0, timeout=86400)
        # Should not raise
        service._check_budget()


class TestAnalyzeNews:
    """Test news analysis API call."""

    def setup_method(self):
        cache.clear()

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_analyze_news_returns_articles(self, mock_client_prop):
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client

        expected = {
            "articles": [
                {
                    "title": "Test News",
                    "sentiment": 0.6,
                    "factors": ["positive earnings"],
                    "impact": "short-term bullish",
                }
            ]
        }
        mock_client.chat.completions.create.return_value = _mock_completion(
            expected
        )

        service = AIService()
        result = service.analyze_news(
            "000001", "平安银行", [{"title": "Test News", "content": "Good results"}]
        )
        assert "articles" in result
        assert len(result["articles"]) == 1
        assert result["articles"][0]["sentiment"] == 0.6

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_analyze_news_limits_articles(self, mock_client_prop):
        """Only first 10 articles are sent to the API."""
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_completion(
            {"articles": []}
        )

        service = AIService()
        # Provide 15 articles
        articles = [{"title": f"Article {i}"} for i in range(15)]
        service.analyze_news("000001", "平安银行", articles)

        # Verify the user prompt only contains 10 articles
        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert user_msg.count("Title:") == 10


class TestAnalyzeFinancial:
    """Test financial analysis API call."""

    def setup_method(self):
        cache.clear()

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_analyze_financial_returns_score(self, mock_client_prop):
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client

        expected = {
            "score": 80,
            "strengths": ["Strong revenue growth"],
            "weaknesses": ["High debt ratio"],
            "recommendation": "Hold",
        }
        mock_client.chat.completions.create.return_value = _mock_completion(
            expected
        )

        service = AIService()
        result = service.analyze_financial(
            "000001", "平安银行", {"revenue": 100000, "profit": 20000}
        )

        assert result["score"] == 80
        assert "strengths" in result
        assert "weaknesses" in result
        assert "recommendation" in result


class TestScoreFactors:
    """Test factor scoring API call."""

    def setup_method(self):
        cache.clear()

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_score_factors_returns_adjusted(self, mock_client_prop):
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client

        expected = {
            "adjusted_score": 72,
            "reasoning": "Cross-factor analysis suggests lower score",
            "risk_factors": ["Market volatility"],
            "catalysts": ["New product launch"],
        }
        mock_client.chat.completions.create.return_value = _mock_completion(
            expected
        )

        service = AIService()
        result = service.score_factors(
            "000001",
            "平安银行",
            {"technical": 75, "fundamental": 80, "sentiment": 60},
        )

        assert result["adjusted_score"] == 72
        assert "reasoning" in result
        assert "risk_factors" in result
        assert "catalysts" in result


class TestGenerateReport:
    """Test report generation API call."""

    def setup_method(self):
        cache.clear()

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_generate_report_returns_sections(self, mock_client_prop):
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client

        expected = {
            "summary": "Overall positive outlook",
            "technical": "Upward trend confirmed",
            "fundamental": "Strong financials",
            "risks": ["Regulatory changes"],
            "recommendation": "Buy with caution",
        }
        mock_client.chat.completions.create.return_value = _mock_completion(
            expected
        )

        service = AIService()
        result = service.generate_report(
            "000001",
            "平安银行",
            {"score": 75, "sentiment": 0.6},
        )

        assert result["summary"] == "Overall positive outlook"
        assert "technical" in result
        assert "fundamental" in result
        assert "risks" in result
        assert "recommendation" in result

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_generate_report_uses_higher_max_tokens(self, mock_client_prop):
        """Report generation uses max_tokens=4000."""
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_completion(
            {"summary": "test"}
        )

        service = AIService()
        service.generate_report("000001", "平安银行", {"score": 75})

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["max_tokens"] == 4000


class TestAPIErrors:
    """Test error handling in API calls."""

    def setup_method(self):
        cache.clear()

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_api_error_raises_service_error(self, mock_client_prop):
        """API exceptions are wrapped in AIServiceError."""
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError(
            "Connection failed"
        )

        service = AIService()
        with pytest.raises(AIServiceError, match="API call failed"):
            service.analyze_news("000001", "平安银行", [{"title": "test"}])

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_invalid_json_response(self, mock_client_prop):
        """Non-JSON response raises AIServiceError."""
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not JSON"
        mock_response.usage.total_tokens = 100
        mock_client.chat.completions.create.return_value = mock_response

        service = AIService()
        with pytest.raises(AIServiceError, match="Invalid JSON response"):
            service.analyze_news("000001", "平安银行", [{"title": "test"}])

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_budget_exceeded_blocks_api_call(self, mock_client_prop):
        """API call is not made when budget is exceeded."""
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client

        service = AIService()
        key = service._get_budget_key()
        cache.set(key, 10.0, timeout=86400)  # Exceed budget

        with pytest.raises(BudgetExceededError):
            service.analyze_news("000001", "平安银行", [{"title": "test"}])

        # Verify no API call was made
        mock_client.chat.completions.create.assert_not_called()

    @patch.object(AIService, "client", new_callable=PropertyMock)
    def test_budget_exceeded_propagates_through_call_api(self, mock_client_prop):
        """BudgetExceededError propagates without being caught by generic handler."""
        mock_client = MagicMock()
        mock_client_prop.return_value = mock_client

        service = AIService()
        key = service._get_budget_key()
        cache.set(key, 10.0, timeout=86400)

        with pytest.raises(BudgetExceededError):
            service._call_api("system", "user")


class TestPrompts:
    """Test prompt templates."""

    def test_prompts_importable(self):
        """All prompts can be imported."""
        from apps.quant.ai.prompts import (
            FACTOR_SCORING_PROMPT,
            FINANCIAL_ANALYSIS_PROMPT,
            NEWS_ANALYSIS_PROMPT,
            REPORT_GENERATION_PROMPT,
            SYSTEM_PROMPT_BASE,
        )

        assert "A-share" in SYSTEM_PROMPT_BASE
        assert "{stock_code}" in NEWS_ANALYSIS_PROMPT
        assert "{financial_data}" in FINANCIAL_ANALYSIS_PROMPT
        assert "{factor_data}" in FACTOR_SCORING_PROMPT
        assert "{analysis_data}" in REPORT_GENERATION_PROMPT

    def test_news_prompt_format(self):
        """NEWS_ANALYSIS_PROMPT can be formatted with stock_code and stock_name."""
        from apps.quant.ai.prompts import NEWS_ANALYSIS_PROMPT

        result = NEWS_ANALYSIS_PROMPT.format(
            stock_code="000001", stock_name="平安银行"
        )
        assert "000001" in result
        assert "平安银行" in result

    def test_financial_prompt_format(self):
        """FINANCIAL_ANALYSIS_PROMPT can be formatted."""
        from apps.quant.ai.prompts import FINANCIAL_ANALYSIS_PROMPT

        result = FINANCIAL_ANALYSIS_PROMPT.format(
            stock_code="000001",
            stock_name="平安银行",
            financial_data='{"revenue": 100000}',
        )
        assert "000001" in result
        assert "revenue" in result

    def test_factor_prompt_format(self):
        """FACTOR_SCORING_PROMPT can be formatted."""
        from apps.quant.ai.prompts import FACTOR_SCORING_PROMPT

        result = FACTOR_SCORING_PROMPT.format(
            stock_code="000001",
            stock_name="平安银行",
            factor_data='{"technical": 75}',
        )
        assert "000001" in result
        assert "technical" in result

    def test_report_prompt_format(self):
        """REPORT_GENERATION_PROMPT can be formatted."""
        from apps.quant.ai.prompts import REPORT_GENERATION_PROMPT

        result = REPORT_GENERATION_PROMPT.format(
            stock_code="000001",
            stock_name="平安银行",
            analysis_data='{"score": 75}',
        )
        assert "000001" in result
        assert "score" in result


class TestModuleInit:
    """Test module __init__.py exports."""

    def test_ai_service_importable_from_package(self):
        """AIService can be imported from apps.quant.ai."""
        from apps.quant.ai import AIService as AI

        assert AI is AIService
