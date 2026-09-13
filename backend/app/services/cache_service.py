import json
import logging
from typing import Optional, Any, Callable, Awaitable
from app.db.redis import redis_manager

logger = logging.getLogger("hireprep.cache_service")

class CacheService:
    """
    Central distributed caching service for HirePrep_AI.
    Manages key namespaces, TTL policies, and JSON serialization.
    """
    # TTL Policies (in seconds)
    PROFILE_TTL = 43200           # 12 hours (GitHub / LeetCode profile scrape)
    WEB_INTEL_TTL = 86400         # 24 hours (Reddit, HN, LeetCode Discuss intelligence)
    QUESTION_BANK_TTL = 604800    # 7 days (Standard company interview question banks)
    INTERVIEW_SESSION_TTL = 7200  # 2 hours (Live interview transient state)

    @staticmethod
    def profile_key(platform: str, handle: str) -> str:
        return f"cache:profile:{platform.lower().strip()}:{handle.lower().strip()}"

    @staticmethod
    def web_intel_key(company: str, role: str) -> str:
        c = company.lower().strip().replace(" ", "_")
        r = role.lower().strip().replace(" ", "_")
        return f"cache:web_intel:{c}:{r}"

    @staticmethod
    def question_bank_key(company: str, role: str, experience_level: str) -> str:
        c = company.lower().strip().replace(" ", "_")
        r = role.lower().strip().replace(" ", "_")
        lvl = experience_level.lower().strip().replace(" ", "_")
        return f"cache:qbank:{c}:{r}:{lvl}"

    @staticmethod
    def rate_limit_key(identifier: str, endpoint: str) -> str:
        return f"ratelimit:{endpoint}:{identifier}"

    async def get_json(self, key: str) -> Optional[Any]:
        """Fetch and deserialize JSON object from cache."""
        raw = await redis_manager.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Failed to deserialize cached JSON for {key}: {e}")
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Serialize and store JSON object in cache with TTL."""
        try:
            serialized = json.dumps(value)
            return await redis_manager.set(key, serialized, ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Failed to serialize and cache JSON for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete an item from cache."""
        return await redis_manager.delete(key)

    async def get_or_set_json(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        ttl_seconds: int = 3600
    ) -> tuple[Any, bool]:
        """
        Cache-aside pattern helper.
        Returns: (data, is_cache_hit: bool)
        """
        cached = await self.get_json(key)
        if cached is not None:
            return cached, True

        data = await fetcher()
        if data is not None:
            await self.set_json(key, data, ttl_seconds=ttl_seconds)
        return data, False

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: int = 30,
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Enforce rate limits per user or IP for costly operations.
        Returns: (is_allowed: bool, remaining_tokens: int)
        """
        key = self.rate_limit_key(identifier, endpoint)
        return await redis_manager.check_rate_limit(key, limit, window_seconds)

    @property
    def is_redis_active(self) -> bool:
        return redis_manager.is_connected_to_redis

cache_service = CacheService()
