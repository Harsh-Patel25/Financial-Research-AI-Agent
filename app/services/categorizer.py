"""
Categorization Service.
Determines the intent of a user query: 'stock', 'news', 'portfolio', or 'general'.
"""

import logging
from typing import Literal

# TODO: Import actual LLM client in Task 4
# from app.core.llm import completion

logger = logging.getLogger(__name__)

Category = Literal["stock", "news", "portfolio", "general"]
VALID_CATEGORIES = {"stock", "news", "portfolio", "general"}

SYSTEM_PROMPT = """You are a financial intent classifier.
Classify the following query into exactly ONE of these categories:
- stock: questions about stock price, technical indicators, company financials.
- news: questions about market news, recent events, sentiment.
- portfolio: questions about current holdings, adding/removing stocks, performance.
- general: greeting, definitions, or queries unrelated to specific financial data.

Output strictly the category name in lowercase. No punctuation, no explanation.
"""

async def categorize_query(query: str) -> Category:
    """
    Classifies the user query using an LLM (mocked for now).
    Falls back to 'general' on failure.
    """
    try:
        # TODO: Replace with actual LLM call in Task 12/4
        # response = await llm.complete(SYSTEM_PROMPT, query, temperature=0)
        # category = response.strip().lower()
        
        # Temporary deterministic logic for testing until LLM is wired
        q = query.lower()
        
        # Stock keywords
        if any(x in q for x in ["price", "pe ratio", "dividend", "volume", "chart", "high", "low", "market cap"]):
            return "stock"
            
        # News keywords
        if any(x in q for x in ["news", "headline", "happened", "event", "latest", "update", "report"]):
            return "news"
            
        # Portfolio keywords
        if any(x in q for x in ["portfolio", "holding", "bought", "sold", "buy", "sell", "balance", "account", "transaction", "position"]):
            return "portfolio"
            
        # If we had an LLM response check:
        # if category not in VALID_CATEGORIES:
        #     logger.warning(f"Invalid category '{category}' from LLM. Fallback to 'general'.")
        #     return "general"
        
        return "general"

    except Exception as e:
        logger.error(f"Categorization failed: {e}")
        return "general"
