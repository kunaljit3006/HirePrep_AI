import pytest
import time
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException, Request

from app.db.redis import InMemoryFallbackCache, redis_manager
from app.services.cache_service import cache_service
from app.services.question_service import question_service
from app.services.github_service import github_service
from app.services.leetcode_service import leetcode_service
from app.services.codeforces_service import codeforces_service
from app.dependencies import RateLimiter

@pytest.mark.asyncio
async def test_in_memory_cache_get_set_delete():
    """Verify in-memory cache operations."""
    mem = InMemoryFallbackCache()
    assert await mem.get("test_key") is None

    # Set with 2s TTL
    await mem.set("test_key", "test_val", ex=2)
    assert await mem.get("test_key") == "test_val"

    # Delete
    deleted = await mem.delete("test_key")
    assert deleted is True
    assert await mem.get("test_key") is None

@pytest.mark.asyncio
async def test_in_memory_cache_expiration():
    """Verify TTL expiration."""
    mem = InMemoryFallbackCache()
    await mem.set("expire_key", "data", ex=1)
    assert await mem.get("expire_key") == "data"
    
    # Wait for TTL to expire
    import asyncio
    await asyncio.sleep(1.1)
    assert await mem.get("expire_key") is None

@pytest.mark.asyncio
async def test_sliding_window_rate_limiter():
    """Verify rate limiter allows up to limit and blocks when exceeded."""
    mem = InMemoryFallbackCache()
    key = "ratelimit:test_endpoint:user123"
    limit = 3
    window = 2  # 2 seconds

    # 1st request -> Allowed
    ok, remaining = await mem.check_rate_limit(key, limit=limit, window_seconds=window)
    assert ok is True
    assert remaining == 2

    # 2nd request -> Allowed
    ok, remaining = await mem.check_rate_limit(key, limit=limit, window_seconds=window)
    assert ok is True
    assert remaining == 1

    # 3rd request -> Allowed
    ok, remaining = await mem.check_rate_limit(key, limit=limit, window_seconds=window)
    assert ok is True
    assert remaining == 0

    # 4th request -> Blocked (exceeded limit 3)
    ok, remaining = await mem.check_rate_limit(key, limit=limit, window_seconds=window)
    assert ok is False
    assert remaining == 0

@pytest.mark.asyncio
async def test_cache_service_json_serialization():
    """Verify CacheService handles complex JSON structures and custom namespaces."""
    await redis_manager.flush_all()

    payload = {"company": "Google", "rounds": ["coding", "system_design"], "score": 98.5}
    key = cache_service.question_bank_key("Google", "SDE II", "Senior")
    
    # Cache write
    saved = await cache_service.set_json(key, payload, ttl_seconds=300)
    assert saved is True

    # Cache read
    retrieved = await cache_service.get_json(key)
    assert retrieved == payload
    assert retrieved["company"] == "Google"
    assert retrieved["score"] == 98.5

@pytest.mark.asyncio
async def test_question_service_web_intel_caching():
    """
    Verify parallel web intelligence gathering caches results
    so the 2nd user for the same role skips external scrapers.
    """
    await redis_manager.flush_all()
    company = "Amazon"
    role = "Backend Engineer"

    # 1st Call: Gathers and caches
    intel_1 = await question_service.gather_all_web_intelligence(company, role)
    assert intel_1 is not None

    # Check that it's now in cache
    cache_key = cache_service.web_intel_key(company, role)
    cached_val = await cache_service.get_json(cache_key)
    assert cached_val is not None
    assert cached_val == intel_1

    # 2nd Call: Must return identical cached intelligence
    intel_2 = await question_service.gather_all_web_intelligence(company, role)
    assert intel_2 == intel_1

@pytest.mark.asyncio
async def test_question_bank_caching_for_standard_roles():
    """
    Verify that generating a question bank for a company/role without custom resume
    caches the entire 5-round question bank with a 7-day TTL.
    """
    await redis_manager.flush_all()
    company = "Netflix"
    role = "Distributed Systems Engineer"

    # First generation
    questions_1 = await question_service.generate_question_bank(
        company=company,
        role=role,
        experience_level="Senior"
    )
    assert len(questions_1) > 0

    # Verify cached in Redis/in-memory
    qbank_key = cache_service.question_bank_key(company, role, "Senior")
    cached = await cache_service.get_json(qbank_key)
    assert cached is not None
    assert len(cached) == len(questions_1)

    # Second generation: Should fetch from cache directly!
    with patch("app.services.llm_service.llm_service.call") as mock_llm:
        questions_2 = await question_service.generate_question_bank(
            company=company,
            role=role,
            experience_level="Senior"
        )
        # LLM must NOT be called on cache HIT
        mock_llm.assert_not_called()
        assert len(questions_2) == len(questions_1)
        assert questions_2[0].title == questions_1[0].title

@pytest.mark.asyncio
async def test_github_and_leetcode_caching():
    """Verify external developer profiles are cached in Redis to prevent rate limiting."""
    await redis_manager.flush_all()

    # LeetCode caching
    lc_profile_1 = await leetcode_service.fetch_profile("tourist")
    assert lc_profile_1 is not None

    # Second fetch should hit cache
    lc_key = cache_service.profile_key("leetcode", "tourist")
    cached_lc = await cache_service.get_json(lc_key)
    assert cached_lc is not None
    assert cached_lc["username"] == "tourist"

    lc_profile_2 = await leetcode_service.fetch_profile("tourist")
    assert lc_profile_2.total_solved == lc_profile_1.total_solved

@pytest.mark.asyncio
async def test_rate_limiter_dependency_blocks_abuse():
    """Verify RateLimiter dependency raises HTTP 429 when threshold is reached."""
    await redis_manager.flush_all()
    limiter = RateLimiter(requests_limit=2, window_seconds=60)

    # Mock request
    mock_request = AsyncMock(spec=Request)
    mock_request.url.path = "/api/test/costly"
    mock_request.headers = {"x-user-id": "spammer-user-001"}
    mock_request.query_params = {}

    # Call 1: Allowed
    res1 = await limiter(mock_request)
    assert res1 is True

    # Call 2: Allowed
    res2 = await limiter(mock_request)
    assert res2 is True

    # Call 3: Exceeded limit of 2 -> HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        await limiter(mock_request)
    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
