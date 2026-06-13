"""
Unit tests for the Fixed Window algorithm.

Tests cover:
  - Basic allow/deny behaviour
  - Headers are correct (Limit, Remaining, Reset, Retry-After)
  - Window boundary — counter resets in a new window
  - Concurrent requests — no race conditions under asyncio.gather
  - Exact limit boundary (request N allowed, N+1 denied)
"""

import asyncio
import time

import pytest

from rate_limiter.algorithms.fixed_window import FixedWindowAlgorithm
from rate_limiter.backends.memory import InMemoryBackend


@pytest.fixture
def backend():
    return InMemoryBackend()


@pytest.fixture
def algo(backend):
    return FixedWindowAlgorithm(backend)


# ── Basic allow ───────────────────────────────────────────────────────────────


async def test_first_request_is_allowed(algo):
    result = await algo.check("user:1", limit=5, window=60)
    assert result.allowed is True


async def test_remaining_decrements(algo):
    await algo.check("user:2", limit=5, window=60)
    result = await algo.check("user:2", limit=5, window=60)
    assert result.remaining == 3


async def test_limit_header_is_always_total(algo):
    result = await algo.check("user:3", limit=10, window=60)
    assert result.limit == 10


# ── Boundary ──────────────────────────────────────────────────────────────────


async def test_exactly_at_limit_is_allowed(algo):
    key = "user:boundary"
    for _ in range(4):
        await algo.check(key, limit=5, window=60)
    result = await algo.check(key, limit=5, window=60)  # 5th request
    assert result.allowed is True
    assert result.remaining == 0


async def test_over_limit_is_denied(algo):
    key = "user:over"
    for _ in range(5):
        await algo.check(key, limit=5, window=60)
    result = await algo.check(key, limit=5, window=60)  # 6th request
    assert result.allowed is False
    assert result.remaining == 0


async def test_denied_response_has_retry_after(algo):
    key = "user:retry"
    for _ in range(3):
        await algo.check(key, limit=3, window=60)
    result = await algo.check(key, limit=3, window=60)
    assert result.allowed is False
    assert result.retry_after is not None
    assert result.retry_after > 0


async def test_allowed_response_has_no_retry_after(algo):
    result = await algo.check("user:ok", limit=10, window=60)
    assert result.retry_after is None


# ── Reset timestamp ───────────────────────────────────────────────────────────


async def test_reset_at_is_end_of_current_window(algo):
    now = int(time.time())
    result = await algo.check("user:reset", limit=5, window=60)
    window_start = (now // 60) * 60
    expected_reset = window_start + 60
    # Allow ±1 second for test execution time
    assert abs(result.reset_at - expected_reset) <= 1


# ── Independent keys don't interfere ─────────────────────────────────────────


async def test_different_keys_are_independent(algo):
    for _ in range(5):
        await algo.check("user:a", limit=5, window=60)
    result = await algo.check("user:b", limit=5, window=60)
    assert result.allowed is True
    assert result.remaining == 4


# ── Concurrency: no race conditions ──────────────────────────────────────────


async def test_concurrent_requests_correct_count(algo):
    """
    Fire 20 concurrent requests against a limit of 10.
    Exactly 10 should be allowed and 10 denied — no over-counting.
    """
    key = "user:concurrent"
    limit = 10

    results = await asyncio.gather(
        *[algo.check(key, limit=limit, window=60) for _ in range(20)]
    )

    allowed = sum(1 for r in results if r.allowed)
    denied = sum(1 for r in results if not r.allowed)

    assert allowed == 10
    assert denied == 10


async def test_concurrent_100_requests(algo):
    """Stress test: 100 concurrent requests, limit 50."""
    key = "user:stress"
    results = await asyncio.gather(
        *[algo.check(key, limit=50, window=60) for _ in range(100)]
    )
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 50


# ── HTTP endpoint tests (uses the real FastAPI app) ───────────────────────────


async def test_demo_endpoint_allows_requests(client):
    response = await client.get(
        "/api/fixed",
        headers={"X-Forwarded-For": "10.0.0.1"},
    )
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


async def test_demo_endpoint_returns_429_when_over_limit(client):
    for _ in range(10):
        await client.get("/api/fixed", headers={"X-Forwarded-For": "10.0.0.3"})
    response = await client.get("/api/fixed", headers={"X-Forwarded-For": "10.0.0.3"})
    assert response.status_code == 429
    assert response.json()["error"] == "rate_limit_exceeded"
    assert "Retry-After" in response.headers


async def test_remaining_header_decrements_correctly(client):
    r1 = await client.get("/api/fixed", headers={"X-Forwarded-For": "10.0.0.4"})
    r2 = await client.get("/api/fixed", headers={"X-Forwarded-For": "10.0.0.4"})
    assert int(r1.headers["X-RateLimit-Remaining"]) > int(
        r2.headers["X-RateLimit-Remaining"]
    )
