"""System prompts for AI-powered stock analysis."""

SYSTEM_PROMPT_BASE = (
    "You are an expert A-share (Chinese stock market) analyst. "
    "Respond in Chinese. Be data-driven, concise, and objective."
)

NEWS_ANALYSIS_PROMPT = (
    "Analyze the following financial news articles related to stock {stock_code} ({stock_name}). "
    "For each article, provide:\n"
    "1. Sentiment score: a float from -1.0 (very bearish) to 1.0 (very bullish)\n"
    "2. Key impact factors\n"
    "3. Short-term impact assessment\n\n"
    "Respond in JSON format:\n"
    '{{"articles": [{{"title": "...", "sentiment": 0.5, "factors": ["..."], "impact": "..."}}]}}'
)

FINANCIAL_ANALYSIS_PROMPT = (
    "Analyze the following financial data for stock {stock_code} ({stock_name}):\n\n"
    "{financial_data}\n\n"
    "Provide:\n"
    "1. Overall financial health score (0-100)\n"
    "2. Key strengths and weaknesses\n"
    "3. Investment recommendation\n\n"
    "Respond in JSON format:\n"
    '{{"score": 75, "strengths": ["..."], "weaknesses": ["..."], "recommendation": "..."}}'
)

FACTOR_SCORING_PROMPT = (
    "Given the following multi-factor analysis results for stock {stock_code} ({stock_name}):\n\n"
    "{factor_data}\n\n"
    "As an expert analyst, evaluate and adjust the scores if needed. "
    "Consider cross-factor interactions that quantitative models might miss.\n\n"
    "Respond in JSON format:\n"
    '{{"adjusted_score": 75, "reasoning": "...", "risk_factors": ["..."], "catalysts": ["..."]}}'
)

REPORT_GENERATION_PROMPT = (
    "Generate a comprehensive analysis report for stock {stock_code} ({stock_name}).\n\n"
    "Analysis data:\n{analysis_data}\n\n"
    "Generate a structured report covering:\n"
    "1. Executive summary (2-3 sentences)\n"
    "2. Technical outlook\n"
    "3. Fundamental assessment\n"
    "4. Risk factors\n"
    "5. Actionable recommendation\n\n"
    "Respond in JSON format:\n"
    '{{"summary": "...", "technical": "...", "fundamental": "...", "risks": ["..."], "recommendation": "..."}}'
)
