"""
News Schemas (schemas/news.py)

Pydantic models for normalizing news data from various providers
(NewsAPI, Yahoo Finance RSS, etc.) into a consistent internal format.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, HttpUrl


class NewsArticle(BaseModel):
    """
    Standardized news article format.
    All providers must map their responses to this strict schema.
    """
    title: str
    source: str
    published_at: datetime
    url: HttpUrl
    summary: str = ""  # Optional brief snippet


class NewsResponse(BaseModel):
    """
    Response returned to the router/client, containing a list of articles
    and metadata about the fetch (e.g., if it was served from cache).
    """
    symbol: str
    count: int
    articles: List[NewsArticle]
    cached: bool = False
    provider: str

    model_config = {"from_attributes": True}
