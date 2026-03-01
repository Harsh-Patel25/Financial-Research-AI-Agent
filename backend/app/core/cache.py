import json
import logging
from typing import Any, Optional

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """
    A unified caching layer that attempts to use Redis.
    If Redis is unavailable (e.g., running locally without docker),
    it transparently falls back to an in-memory dictionary.
    """
    def __init__(self):
        self.use_redis = False
        self._memory_cache = {}
        self._memory_ttls = {}
        
        try:
            # We add decode_responses=True so we get strings back instead of bytes
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.use_redis = True
            logger.info(f"Connected to Redis at {settings.redis_url}")
        except redis.ConnectionError:
            logger.warning("Redis is unreachable. Falling back to in-memory dictionary cache.")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}. Falling back to in-memory dictionary cache.")

    def get(self, key: str) -> Optional[Any]:
        """Fetch an item from cache."""
        try:
            if self.use_redis:
                val = self.redis_client.get(key)
                if val is not None:
                    return json.loads(val)
                return None
            else:
                # In-memory fallback (we don't actively expire here for simplicity,
                # but could use time.time() if needed. This is development fallback only.)
                return self._memory_cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get failure for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Store an item in cache with a TTL (Time To Live)."""
        try:
            serialized = json.dumps(value)
            if self.use_redis:
                self.redis_client.setex(key, ttl_seconds, serialized)
                return True
            else:
                # In-memory fallback
                self._memory_cache[key] = value
                return True
        except Exception as e:
            logger.warning(f"Cache set failure for key {key}: {e}")
            return False

    def clear(self):
        """Clear the cache."""
        if self.use_redis:
            self.redis_client.flushdb()
        else:
            self._memory_cache.clear()

# Singleton instance
cache = CacheService()
