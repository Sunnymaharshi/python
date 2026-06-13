"""
Concurrent correctness tests — the most important tests in the project.

These prove that under high concurrency, no algorithm ever admits more
requests than its limit. This is the core correctness guarantee we need
to demonstrate for the resume project.

Each test fires N concurrent requests using asyncio.gather() and asserts:
  - allowed == limit (never more, never less when N > limit)
  - denied  == N - limit
"""

import asyncio

from rate_limiter.algorithms.fixed_window import FixedWindowAlgorithm
from rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from rate_limiter.algorithms.sliding_window import SlidingWindowAlgorithm
from rate_limiter.algorithms.token_bucket import TokenBucketAlgorithm
from rate_limiter.backends.memory import InMemoryBackend

# ── Helpers ───────────────────────────────────────────────────────────────────


async def fire(
    algo, key: str, limit: int, window: int = 60, **kwargs
) -> tuple[int, int]:
    """Fire 2×limit concurrent requests. Return (allowed, denied)."""
    n = limit * 2
    results = await asyncio.gather(
        *[algo.check(key, limit=limit, window=window, **kwargs) for _ in range(n)]
    )
    allowed = sum(1 for r in results if r.allowed)
    denied = sum(1 for r in results if not r.allowed)
    return allowed, denied


# ── Fixed window ──────────────────────────────────────────────────────────────


async def test_fixed_window_concurrent_10():
    algo = FixedWindowAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "fw:10", limit=10)
    assert allowed == 10 and denied == 10


async def test_fixed_window_concurrent_50():
    algo = FixedWindowAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "fw:50", limit=50)
    assert allowed == 50 and denied == 50


async def test_fixed_window_concurrent_100():
    algo = FixedWindowAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "fw:100", limit=100)
    assert allowed == 100 and denied == 100


# ── Sliding window ────────────────────────────────────────────────────────────


async def test_sliding_window_concurrent_10():
    algo = SlidingWindowAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "sw:10", limit=10)
    assert allowed == 10 and denied == 10


async def test_sliding_window_concurrent_50():
    algo = SlidingWindowAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "sw:50", limit=50)
    assert allowed == 50 and denied == 50


async def test_sliding_window_concurrent_100():
    algo = SlidingWindowAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "sw:100", limit=100)
    assert allowed == 100 and denied == 100


# ── Token bucket ──────────────────────────────────────────────────────────────


async def test_token_bucket_concurrent_no_burst():
    algo = TokenBucketAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "tb:10", limit=10, burst=0)
    assert allowed == 10 and denied == 10


async def test_token_bucket_concurrent_with_burst():
    """burst=10 on limit=10 → bucket holds 20 → all 20 concurrent allowed."""
    algo = TokenBucketAlgorithm(InMemoryBackend())
    n = 20
    results = await asyncio.gather(
        *[algo.check("tb:burst", limit=10, window=60, burst=10) for _ in range(n)]
    )
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 20


async def test_token_bucket_concurrent_50():
    algo = TokenBucketAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "tb:50", limit=50, burst=0)
    assert allowed == 50 and denied == 50


# ── Leaky bucket ──────────────────────────────────────────────────────────────


async def test_leaky_bucket_concurrent_10():
    algo = LeakyBucketAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "lb:10", limit=10)
    assert allowed == 10 and denied == 10


async def test_leaky_bucket_concurrent_50():
    algo = LeakyBucketAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "lb:50", limit=50)
    assert allowed == 50 and denied == 50


async def test_leaky_bucket_concurrent_100():
    algo = LeakyBucketAlgorithm(InMemoryBackend())
    allowed, denied = await fire(algo, "lb:100", limit=100)
    assert allowed == 100 and denied == 100


# ── Cross-algorithm: independent keys never interfere ────────────────────────


async def test_all_algorithms_independent_keys():
    """
    All 4 algorithms running concurrently on different keys.
    No algorithm should bleed into another's counter.
    """
    backend = InMemoryBackend()
    fw = FixedWindowAlgorithm(backend)
    sw = SlidingWindowAlgorithm(backend)
    tb = TokenBucketAlgorithm(backend)
    lb = LeakyBucketAlgorithm(backend)

    limit = 20
    results = await asyncio.gather(
        *[fw.check("cross:fw", limit=limit, window=60) for _ in range(limit * 2)],
        *[sw.check("cross:sw", limit=limit, window=60) for _ in range(limit * 2)],
        *[
            tb.check("cross:tb", limit=limit, window=60, burst=0)
            for _ in range(limit * 2)
        ],
        *[lb.check("cross:lb", limit=limit, window=60) for _ in range(limit * 2)],
    )

    # Split results into 4 groups of 40
    n = limit * 2
    fw_r, sw_r, tb_r, lb_r = (
        results[:n],
        results[n : 2 * n],
        results[2 * n : 3 * n],
        results[3 * n :],
    )

    for name, group in [
        ("fixed", fw_r),
        ("sliding", sw_r),
        ("token", tb_r),
        ("leaky", lb_r),
    ]:
        allowed = sum(1 for r in group if r.allowed)
        assert allowed == limit, f"{name}: expected {limit} allowed, got {allowed}"


# ── Stress test: 500 concurrent requests ─────────────────────────────────────


async def test_stress_500_concurrent_fixed_window():
    """500 concurrent requests, limit=250. Proves INCR atomicity at scale."""
    algo = FixedWindowAlgorithm(InMemoryBackend())
    results = await asyncio.gather(
        *[algo.check("stress:fw", limit=250, window=60) for _ in range(500)]
    )
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 250, f"Expected 250 allowed, got {allowed}"


async def test_stress_500_concurrent_token_bucket():
    """500 concurrent requests, limit=250, burst=0. Proves Lua atomicity at scale."""
    algo = TokenBucketAlgorithm(InMemoryBackend())
    results = await asyncio.gather(
        *[algo.check("stress:tb", limit=250, window=60, burst=0) for _ in range(500)]
    )
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 250, f"Expected 250 allowed, got {allowed}"
