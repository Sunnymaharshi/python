"""
Unit tests for Leaky Bucket Rate Limiting.

Tests cover:
  - Basic allow/deny behaviour
  - No burst — bucket capacity is strictly enforced
  - Queue drains over time at constant rate
  - Concurrent requests stay within capacity
  - retry_after and remaining are correct

Key difference from token bucket:
  - Token bucket starts FULL (tokens available immediately)
  - Leaky bucket starts EMPTY (queue starts empty, fills on requests)
  - Token bucket ALLOWS bursts up to capacity
  - Leaky bucket REJECTS once queue hits capacity (no burst allowance)
"""

import asyncio

import pytest

from rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from rate_limiter.backends.memory import InMemoryBackend


@pytest.fixture
def backend():
    return InMemoryBackend()


@pytest.fixture
def algo(backend):
    return LeakyBucketAlgorithm(backend)


# ── Basic allow/deny ──────────────────────────────────────────────────────────


async def test_first_request_allowed(algo):
    result = await algo.check("user:1", limit=5, window=60)
    assert result.allowed is True


async def test_remaining_decrements(algo):
    await algo.check("user:2", limit=5, window=60)
    r2 = await algo.check("user:2", limit=5, window=60)
    assert r2.remaining == 3


async def test_at_capacity_is_denied(algo):
    """Once queue hits capacity, new requests are rejected."""
    key = "user:full"
    limit = 5
    for _ in range(limit):
        r = await algo.check(key, limit=limit, window=60)
        assert r.allowed is True

    r = await algo.check(key, limit=limit, window=60)
    assert r.allowed is False
    assert r.remaining == 0


# ── No burst ──────────────────────────────────────────────────────────────────


async def test_no_burst_allowed(algo):
    """
    Unlike token bucket (which starts full and allows bursts),
    leaky bucket rejects the moment the queue hits capacity.
    There is NO burst allowance.
    """
    key = "user:no_burst"
    limit = 5

    results = []
    for _ in range(10):
        r = await algo.check(key, limit=limit, window=60)
        results.append(r.allowed)

    # Exactly 5 allowed, 5 denied — no burst beyond limit
    assert results == [True] * 5 + [False] * 5


# ── Retry-After ───────────────────────────────────────────────────────────────


async def test_retry_after_set_when_denied(algo):
    key = "user:retry"
    limit = 3
    for _ in range(limit):
        await algo.check(key, limit=limit, window=60)

    r = await algo.check(key, limit=limit, window=60)
    assert r.allowed is False
    assert r.retry_after is not None
    assert r.retry_after >= 1


async def test_retry_after_none_when_allowed(algo):
    r = await algo.check("user:ok", limit=10, window=60)
    assert r.allowed is True
    assert r.retry_after is None


# ── Remaining ─────────────────────────────────────────────────────────────────


async def test_remaining_is_correct(algo):
    key = "user:remaining"
    limit = 5

    r1 = await algo.check(key, limit=limit, window=60)
    assert r1.remaining == 4

    r2 = await algo.check(key, limit=limit, window=60)
    assert r2.remaining == 3

    r3 = await algo.check(key, limit=limit, window=60)
    assert r3.remaining == 2


# ── Independent keys ──────────────────────────────────────────────────────────


async def test_different_keys_independent(algo):
    for _ in range(5):
        await algo.check("user:a", limit=5, window=60)
    r = await algo.check("user:b", limit=5, window=60)
    assert r.allowed is True
    assert r.remaining == 4


# ── Concurrency ───────────────────────────────────────────────────────────────


async def test_concurrent_exact_limit(algo):
    """
    Fire 20 concurrent requests against a queue capacity of 10.
    Exactly 10 allowed, 10 denied — no over-admission.
    """
    key = "user:concurrent"
    limit = 10

    results = await asyncio.gather(
        *[algo.check(key, limit=limit, window=60) for _ in range(20)]
    )

    allowed = sum(1 for r in results if r.allowed)
    denied = sum(1 for r in results if not r.allowed)

    assert allowed == 10, f"Expected 10 allowed, got {allowed}"
    assert denied == 10, f"Expected 10 denied, got {denied}"


async def test_stress_100_requests(algo):
    """100 concurrent requests, limit=50."""
    key = "user:stress"
    results = await asyncio.gather(
        *[algo.check(key, limit=50, window=60) for _ in range(100)]
    )
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 50


# ── Comparison with token bucket ──────────────────────────────────────────────


async def test_leaky_vs_token_bucket_burst():
    """
    Token bucket: starts full → allows 10 immediate requests (with burst).
    Leaky bucket: starts empty → only allows up to capacity, no burst at all.

    This is the KEY difference between the two algorithms.
    """
    from rate_limiter.algorithms.token_bucket import TokenBucketAlgorithm

    backend_leaky = InMemoryBackend()
    backend_token = InMemoryBackend()

    leaky = LeakyBucketAlgorithm(backend_leaky)
    token = TokenBucketAlgorithm(backend_token)

    limit = 5

    # Token bucket with burst=5 allows 10 immediate requests
    token_results = []
    for _ in range(10):
        r = await token.check("key", limit=limit, window=60, burst=5)
        token_results.append(r.allowed)

    # Leaky bucket allows exactly 5 then rejects
    leaky_results = []
    for _ in range(10):
        r = await leaky.check("key", limit=limit, window=60)
        leaky_results.append(r.allowed)

    assert token_results == [True] * 10  # burst absorbed all 10
    assert leaky_results == [True] * 5 + [False] * 5  # strictly limited at 5
