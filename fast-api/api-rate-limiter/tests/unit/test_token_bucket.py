"""
Unit tests for Token Bucket Rate Limiting.

Tests cover:
  - Basic allow/deny with refill
  - Burst allowance — exceeding limit momentarily
  - Token accumulation over time
  - Concurrent requests (Lua atomicity)
  - Smooth rate vs burst spike
"""

import asyncio

import pytest

from rate_limiter.algorithms.token_bucket import TokenBucketAlgorithm
from rate_limiter.backends.memory import InMemoryBackend


@pytest.fixture
def backend():
    return InMemoryBackend()


@pytest.fixture
def algo(backend):
    return TokenBucketAlgorithm(backend)


# ── Basic allow/deny ──────────────────────────────────────────────────────────


async def test_first_request_allowed(algo):
    """With burst=0, bucket holds exactly `limit` tokens."""
    result = await algo.check("user:1", limit=5, window=60, burst=0)
    assert result.allowed is True
    assert result.remaining == 4


async def test_tokens_consumed(algo):
    await algo.check("user:2", limit=5, window=60, burst=0)
    r2 = await algo.check("user:2", limit=5, window=60, burst=0)
    assert r2.remaining == 3


# ── Burst allowance ───────────────────────────────────────────────────────────


async def test_burst_allowance(algo):
    """
    With burst=5, the bucket can hold 10 tokens (limit=5 + burst=5).
    This allows a brief spike of 10 requests, then it settles to 5/60s.
    """
    key = "user:burst"
    limit = 5
    burst = 5

    # Allow 10 requests due to burst
    for i in range(10):
        r = await algo.check(key, limit=limit, window=60, burst=burst)
        assert r.allowed is True, f"Request {i + 1} should be allowed (burst bucket)"

    # 11th request denied (bucket empty)
    r = await algo.check(key, limit=limit, window=60, burst=burst)
    assert r.allowed is False


async def test_limit_without_burst(algo):
    """Without burst (burst=0), bucket capacity = limit. Only 5 tokens available."""
    key = "user:no_burst"
    limit = 5

    for i in range(5):
        r = await algo.check(key, limit=limit, window=60, burst=0)
        assert r.allowed is True

    r = await algo.check(key, limit=limit, window=60, burst=0)
    assert r.allowed is False


# ── Rate limiting over time ───────────────────────────────────────────────────


async def test_smooth_rate_limit(algo):
    """After bucket empties, refill happens at the configured rate."""
    key = "user:smooth"
    limit = 10
    window = 60

    # Consume everything
    for _ in range(limit):
        await algo.check(key, limit=limit, window=window, burst=0)

    # All denied now
    r = await algo.check(key, limit=limit, window=window, burst=0)
    assert r.allowed is False


# ── Concurrency ───────────────────────────────────────────────────────────────


async def test_concurrent_under_capacity(algo):
    """Fire 20 concurrent requests against a 10-token bucket (burst=0)."""
    key = "user:concurrent"
    limit = 10

    results = await asyncio.gather(
        *[algo.check(key, limit=limit, window=60, burst=0) for _ in range(20)]
    )

    allowed = sum(1 for r in results if r.allowed)
    denied = sum(1 for r in results if not r.allowed)

    assert allowed == 10, f"Expected 10 allowed, got {allowed}"
    assert denied == 10, f"Expected 10 denied, got {denied}"


async def test_concurrent_with_burst(algo):
    """With burst, 20 concurrent against a 10-token bucket (limit=5, burst=5)."""
    key = "user:burst_concurrent"
    limit = 5
    burst = 5

    results = await asyncio.gather(
        *[algo.check(key, limit=limit, window=60, burst=burst) for _ in range(10)]
    )

    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 10, f"Expected 10 allowed (burst), got {allowed}"

    # 11th request should be denied
    r = await asyncio.gather(algo.check(key, limit=limit, window=60, burst=burst))
    assert r[0].allowed is False


async def test_stress_concurrent_requests(algo):
    """High-load test: 100 concurrent requests against limit=50 (burst=0)."""
    key = "user:stress"
    results = await asyncio.gather(
        *[algo.check(key, limit=50, window=60, burst=0) for _ in range(100)]
    )
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 50


# ── Headers and reset_at ──────────────────────────────────────────────────────


async def test_retry_after_when_denied(algo):
    """When a request is denied, retry_after should be set."""
    key = "user:retry"
    limit = 3

    # Consume all tokens
    for _ in range(limit):
        await algo.check(key, limit=limit, window=60, burst=0)

    # Denied request should have retry_after
    r = await algo.check(key, limit=limit, window=60, burst=0)
    assert r.allowed is False
    assert r.retry_after is not None
    assert r.retry_after > 0


async def test_no_retry_after_when_allowed(algo):
    """When a request is allowed, retry_after should be None."""
    r = await algo.check("user:ok", limit=10, window=60, burst=0)
    assert r.allowed is True
    assert r.retry_after is None


async def test_remaining_token_count(algo):
    """Remaining should reflect actual tokens left in bucket."""
    key = "user:remaining"
    limit = 5

    r1 = await algo.check(key, limit=limit, window=60, burst=0)
    assert r1.remaining == 4

    r2 = await algo.check(key, limit=limit, window=60, burst=0)
    assert r2.remaining == 3


# ── Comparison with other algorithms ───────────────────────────────────────────


async def test_token_bucket_allows_bursts(algo):
    """
    Key difference: token bucket *allows* brief bursts.
    With burst=5, you can make 10 fast requests if the bucket was full.
    Fixed window would reject after 5. Sliding window would also reject after 5.
    Token bucket smooths the spike.
    """
    key = "user:burst_test"
    limit = 5
    burst = 5

    # Make 10 rapid requests (all allowed due to burst)
    results = []
    for _ in range(10):
        r = await algo.check(key, limit=limit, window=60, burst=burst)
        results.append(r.allowed)

    # 11th denied
    r = await algo.check(key, limit=limit, window=60, burst=burst)
    results.append(r.allowed)

    expected = [True] * 10 + [False]
    assert results == expected, f"Expected burst pattern {expected}, got {results}"
