"""
News Service (services/news_service.py)

Fetches, normalizes, and caches relevant financial news for a given stock symbol.

Features:
- Primary source: Yahoo Finance RSS feed (free, no API keys, very reliable)
- Normalizes output to schemas.news.NewsArticle
- In-memory LRU cache with TTL (Time To Live) to prevent spamming the provider
- Fallback/Error handling: Returns empty list instead of crashing if feed fails
"""

import logging
import urllib.parse
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any

import feedparser
from pydantic import ValidationError

from app.schemas.news import NewsArticle, NewsResponse

logger = logging.getLogger(__name__)


class NewsService:
    """
    Stateful service (holds in-memory cache) for fetching targeted financial news.
    """

    def __init__(self, provider_name: str = "YahooFinanceRSS"):
        self.provider_name = provider_name
        self._cache_store: Dict[str, Dict[str, Any]] = {}
        # Simple dict cache: { "AAPL": {"timestamp": 1234567, "response": NewsResponse} }

    # ── In-Memory Caching (LRU style logic for semi-static data) ──────────────

    def _get_from_cache(self, symbol: str, ttl_minutes: int) -> NewsResponse | None:
        """Returns cached NewsResponse if it exists and is not expired."""
        cached_entry = self._cache_store.get(symbol)
        if not cached_entry:
            return None

        # Check TTL
        elapsed = (datetime.now() - cached_entry["timestamp"]).total_seconds()
        if elapsed < (ttl_minutes * 60):
            logger.info("News cache HIT | symbol=%s | age=%.1fm", symbol, elapsed / 60)
            # Return a copy but mark as served from cache
            response = cached_entry["response"].model_copy(update={"cached": True})
            return response
        
        # Expired
        logger.debug("News cache EXPIRED | symbol=%s", symbol)
        del self._cache_store[symbol]
        return None

    def _save_to_cache(self, symbol: str, response: NewsResponse) -> None:
        """Stores a fresh NewsResponse into the local cache dict."""
        # Ensure we don't store 'cached: True' in the base item
        base_resp = response.model_copy(update={"cached": False})
        self._cache_store[symbol] = {
            "timestamp": datetime.now(),
            "response": base_resp,
        }

    # ── API Integration ───────────────────────────────────────────────────────

    def get_news_for_symbol(
        self,
        symbol: str, 
        limit: int = 5,
        cache_ttl_minutes: int = 15,
    ) -> NewsResponse:
        """
        Fetches the latest news articles for a stock symbol.
        Checks cache first. If Miss, fetches from RSS, normalizes, caches, and returns.
        
        Args:
            symbol: Stock ticker (e.g., "AAPL").
            limit: Max articles to return (default 5).
            cache_ttl_minutes: How long to cache the result (default 15m).
            
        Returns:
            NewsResponse validated object.
            Never raises exceptions on network failure — returns empty list instead.
        """
        symbol = symbol.upper().strip()

        # 1. Check Cache
        cached = self._get_from_cache(symbol, ttl_minutes=cache_ttl_minutes)
        if cached:
            return cached

        # 2. Cache Miss -> Fetch
        logger.info("News cache MISS | symbol=%s | fetching from %s", symbol, self.provider_name)
        articles = self._fetch_yahoo_rss(symbol, limit)

        # 3. Build Response
        response = NewsResponse(
            symbol=symbol,
            count=len(articles),
            articles=articles,
            cached=False,
            provider=self.provider_name,
        )

        # 4. Save to Cache
        self._save_to_cache(symbol, response)
        return response

    # ── Provider Specific Logic ───────────────────────────────────────────────

    def _fetch_yahoo_rss(self, symbol: str, limit: int) -> list[NewsArticle]:
        """
        Fetches and maps Yahoo Finance RSS feed to our NewsArticle schema.
        We use RSS because it requires no API key and avoids rate limits better than NewsAPI.
        """
        # Encode symbol safely for URL
        encoded_symbol = urllib.parse.quote(symbol)
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={encoded_symbol}&region=US&lang=en-US"

        try:
            feed = feedparser.parse(url)
            
            if feed.bozo:  # bozo = 1 means RSS parsing error (usually 404 or network issue)
                logger.warning(
                    "RSS feed parse error | symbol=%s | bozo_exc=%s", 
                    symbol, feed.get("bozo_exception", "Unknown")
                )
                return []

            articles = []
            for entry in feed.entries[:limit]:
                # Attempt to parse date, fallback to now if missing
                try:
                    # RSS dates are usually RFC 822: "Fri, 19 May 2023 15:30:00 +0000"
                    # feedparser converts it to a time.struct_time tuple
                    published = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                except Exception:
                    published = datetime.now()

                try:
                    article = NewsArticle(
                        title=entry.title,
                        source=entry.get("publisher", "Yahoo Finance"),
                        published_at=published,
                        url=entry.link,
                        summary=entry.get("summary", "")[:500]  # Cap summary length
                    )
                    articles.append(article)
                except ValidationError as ve:
                    logger.debug("Skipping invalid article | symbol=%s | error=%s", symbol, ve)
                    continue

            return articles

        except Exception as exc:
            logger.error("Failed to fetch news | symbol=%s | error=%s", symbol, str(exc))
            # Resilient fallback: empty list, no crash
            return []


# ── Module-level singleton ────────────────────────────────────────────────────
# Keeps the in-memory cache alive across requests in FastAPI
news_service = NewsService()
