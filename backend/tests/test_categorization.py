"""
Unit Tests – Categorization Service

This module contains unit tests for the `categorize_query` function
located in app/services/categorizer.py.

Purpose:
- Verify that queries are correctly classified into predefined categories.
- Ensure stability and prevent regressions when logic changes.
- Validate fallback behavior for edge cases.

────────────────────────────────────────────

Categories Being Tested:

1) Stock
   Queries related to stock prices, charts, volume, or financial metrics.
   Expected output: "stock"

2) News
   Queries about latest events, headlines, or market updates.
   Expected output: "news"

3) Portfolio
   Queries related to user holdings, transactions, or balances.
   Expected output: "portfolio"

4) General
   Generic or non-financial queries.
   Expected output: "general"

────────────────────────────────────────────

Async Testing

- The `categorize_query` function is asynchronous.
- `@pytest.mark.asyncio` enables pytest to run async test functions.
- Each test awaits the categorization result before asserting.

────────────────────────────────────────────

Test Structure

Each test:
- Defines a list of example queries.
- Iterates through them.
- Asserts that the returned category matches the expected value.

If any query returns an incorrect category,
the test fails immediately.

────────────────────────────────────────────

Fallback & Edge Case Handling

The `test_categorize_fallback` test ensures:
- The function does not crash on empty input.
- The default fallback category ("general") is returned.

This guarantees production safety and defensive behavior.

────────────────────────────────────────────

Why These Tests Matter

✔ Protect against regression errors
✔ Ensure categorization accuracy
✔ Validate async execution flow
✔ Guarantee safe fallback behavior
✔ Provide confidence in the classification layer

This file acts as a quality control layer
for the query categorization module.
"""

import pytest
from app.services.categorizer import categorize_query

@pytest.mark.asyncio
async def test_categorize_stock():
    queries = [
        "What is the price of AAPL?",
        "Show me the chart for Tesla",
        "What is the PE ratio of Microsoft?",
        "Google volume today"
    ]
    for q in queries:
        assert await categorize_query(q) == "stock"

@pytest.mark.asyncio
async def test_categorize_news():
    queries = [
        "Latest news on Apple",
        "What happened to Bitcoin today?",
        "Headlines for NVIDIA",
        "Market events this week"
    ]
    for q in queries:
        assert await categorize_query(q) == "news"

@pytest.mark.asyncio
async def test_categorize_portfolio():
    queries = [
        "Show my portfolio",
        "Add AAPL to my holdings",
        "What did I buy yesterday?",
        "My portfolio balance"
    ]
    for q in queries:
        assert await categorize_query(q) == "portfolio"

@pytest.mark.asyncio
async def test_categorize_general():
    queries = [
        "Hello",
        "What is a stock?",
        "Explain inflation",
        "Who are you?"
    ]
    for q in queries:
        assert await categorize_query(q) == "general"

@pytest.mark.asyncio
async def test_categorize_fallback():
    """Ensure it doesn't crash on empty or weird input."""
    # The current mock implementation returns 'general' for things not matching keywords logic
    res = await categorize_query("")
    assert res == "general"
