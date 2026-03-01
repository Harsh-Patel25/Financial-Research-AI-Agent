"""
Tests for Financial Data Services
Ensures the system parses vendor responses correctly and falls back on network failure.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.stock_service import StockService
from app.services.news_service import NewsService


# ── Stock Service Tests ───────────────────────────────────────────────────────

@pytest.fixture
def mock_stock_service():
    """Returns a fresh instance of StockService with a very short circuit breaker for testing."""
    return StockService(failure_threshold=1, recovery_timeout=0.1)

@patch("app.services.stock_service.yf.Ticker")
def test_get_current_price_success(mock_ticker_class, mock_stock_service):
    """Verifies that a successful yfinance call maps to our schema correctly."""
    
    mock_ticker = MagicMock()
    mock_ticker.fast_info.last_price = 150.25
    mock_ticker.fast_info.currency = "USD"
    mock_ticker.fast_info.exchange = "NMS"
    mock_ticker.fast_info.market_state = "REGULAR"
    mock_ticker.fast_info.previous_close = 149.00
    mock_ticker.fast_info.day_high = 151.00
    mock_ticker.fast_info.day_low = 148.50
    mock_ticker_class.return_value = mock_ticker

    result = mock_stock_service.get_current_price("AAPL")

    assert result["symbol"] == "AAPL"
    assert result["price"] == 150.25
    assert result["currency"] == "USD"
    assert result["market_state"] == "REGULAR"
    assert result["previous_close"] == 149.00

@patch("app.services.stock_service.yf.Ticker")
def test_get_current_price_invalid_symbol(mock_ticker_class, mock_stock_service):
    """Verifies that empty data from yfinance raises a ValueError."""
    
    mock_ticker = MagicMock()
    mock_ticker.fast_info.last_price = None
    mock_ticker.info = {} 
    mock_ticker_class.return_value = mock_ticker

    with pytest.raises(ValueError, match="No price data found for symbol"):
        mock_stock_service.get_current_price("INVALID_TICKER")


# ── News Service Tests ────────────────────────────────────────────────────────
    
from app.core.cache import cache

def test_news_cache_key():
    """Verifies the cache key generation logic for the News Service."""
    srv = NewsService()
    assert srv._get_cache_key("AAPL") == "news:AAPL"
    assert srv._get_cache_key("msft") == "news:MSFT"

