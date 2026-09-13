import logging
import time
from typing import Optional, Any
import json

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from app.config import settings

logger = logging.getLogger("hireprep.redis")

class InMemoryFallbackCache:
    """
    High-performance in-memory TTL dictionary fallback.
    Ensures HirePrep_AI never crashes even if Redis is not installed,
    not running, or in local development without Docker.
    """
    def __init__(self):
        self._store: dict[str, tuple[float, str]] = {}
        self._counters: dict[str, list[float]] = {}  # for rate limiting

    async def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if not item:
            return None
        expire_at, value = item
        if expire_at is not None and time.time() > expire_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        expire_at = (time.time() + ex) if ex else None
        self._store[key] = (expire_at, value)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def flush(self) -> None:
        self._store.clear()
        self._counters.clear()

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Sliding window rate limit implementation in memory."""
        now = time.time()
        timestamps = self._counters.get(key, [])
        # Filter out timestamps older than window
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= limit:
            remaining = 0
            self._counters[key] = timestamps
            return False, remaining
        
        timestamps.append(now)
        self._counters[key] = timestamps
        remaining = limit - len(timestamps)
        return True, remaining


class RedisManager:
    """
    Manages connection to Redis with automatic fallback to InMemoryFallbackCache.
    """
    def __init__(self):
        self._redis_client: Optional[Any] = None
        self._in_memory = InMemoryFallbackCache()
        self._is_redis_active = False

    async def connect(self):
        redis_url = settings.REDIS_URL or "redis://localhost:6379"
        if aioredis:
            try:
                client = aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0
                )
                # Ping test
                await client.ping()
                self._redis_client = client
                self._is_redis_active = True
                logger.info(f"Connected to Redis successfully at {redis_url}")
                return
            except Exception as e:
                logger.warning(
                    f"Redis unavailable at {redis_url} ({e}). "
                    "Seamlessly falling back to high-speed InMemoryCache."
                )
        else:
            logger.info("redis-py not found. Using InMemoryCache fallback.")

        self._redis_client = None
        self._is_redis_active = False

    async def disconnect(self):
        if self._redis_client and self._is_redis_active:
            try:
                await self._redis_client.close()
                logger.info("Redis connection closed cleanly.")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
        self._is_redis_active = False

    @property
    def is_connected_to_redis(self) -> bool:
        return self._is_redis_active

    async def get(self, key: str) -> Optional[str]:
        if self._is_redis_active and self._redis_client:
            try:
                return await self._redis_client.get(key)
            except Exception as e:
                logger.warning(f"Redis get failed for {key}: {e}. Falling back to memory.")
        return await self._in_memory.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        if self._is_redis_active and self._redis_client:
            try:
                return await self._redis_client.set(key, value, ex=ex)
            except Exception as e:
                logger.warning(f"Redis set failed for {key}: {e}. Falling back to memory.")
        return await self._in_memory.set(key, value, ex=ex)

    async def delete(self, key: str) -> bool:
        if self._is_redis_active and self._redis_client:
            try:
                return bool(await self._redis_client.delete(key))
            except Exception as e:
                logger.warning(f"Redis delete failed for {key}: {e}. Falling back to memory.")
        return await self._in_memory.delete(key)

    async def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """
        Sliding window rate limiter using Redis Sorted Sets or in-memory fallback.
        Returns: (allowed: bool, remaining_tokens: int)
        """
        if self._is_redis_active and self._redis_client:
            try:
                now = time.time()
                clear_before = now - window_seconds
                pipe = self._redis_client.pipeline()
                # Remove expired tokens
                pipe.zremrangebyscore(key, 0, clear_before)
                # Count current tokens
                pipe.zcard(key)
                # Add current request timestamp
                pipe.zadd(key, {str(now): now})
                # Set TTL
                pipe.expire(key, window_seconds + 5)
                res = await pipe.execute()
                current_count = res[1]
                if current_count >= limit:
                    # Exceeded
                    return False, 0
                return True, limit - (current_count + 1)
            except Exception as e:
                logger.warning(f"Redis rate limit failed for {key}: {e}. Using memory fallback.")

        return await self._in_memory.check_rate_limit(key, limit, window_seconds)

    async def flush_all(self):
        """Used in test environments to reset cache."""
        if self._is_redis_active and self._redis_client:
            try:
                await self._redis_client.flushdb()
            except Exception:
                pass
        await self._in_memory.flush()


redis_manager = RedisManager()
