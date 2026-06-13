"""
Tests for @rate_limit decorator and RateLimitMiddleware.

All test requests use X-Forwarded-For: 10.0.0.1 to simulate a real
client IP — the default whitelist only covers 127.0.0.1 and ::1.
"""

import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from rate_limiter.algorithms.fixed_window import FixedWindowAlgorithm
from rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from rate_limiter.algorithms.sliding_window import SlidingWindowAlgorithm
from rate_limiter.algorithms.token_bucket import TokenBucketAlgorithm
from rate_limiter.backends.memory import InMemoryBackend
from rate_limiter.middleware.rate_limit import RateLimitMiddleware, rate_limit

# ── Helpers ───────────────────────────────────────────────────────────────────

# Simulate a real client IP — not on the whitelist
CLIENT_IP = {"X-Forwarded-For": "10.0.0.1"}
CLIENT_IP_2 = {"X-Forwarded-For": "10.0.0.2"}


def make_app() -> tuple[FastAPI, InMemoryBackend]:
    backend = InMemoryBackend()
    app = FastAPI()
    app.state.backend = backend
    app.state.fixed_window = FixedWindowAlgorithm(backend)
    app.state.sliding_window = SlidingWindowAlgorithm(backend)
    app.state.token_bucket = TokenBucketAlgorithm(backend)
    app.state.leaky_bucket = LeakyBucketAlgorithm(backend)
    return app, backend


# ── Decorator: headers ────────────────────────────────────────────────────────


async def test_decorator_injects_rate_limit_headers():
    app, _ = make_app()

    @app.get("/test-headers")
    @rate_limit(limit=10, window=60, algorithm="fixed_window", key_by="ip")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get("/test-headers", headers=CLIENT_IP)

    assert r.status_code == 200
    assert r.headers["X-RateLimit-Limit"] == "10"
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-RateLimit-Reset" in r.headers


async def test_decorator_remaining_decrements():
    app, _ = make_app()

    @app.get("/test-decrement")
    @rate_limit(limit=5, window=60, algorithm="fixed_window", key_by="ip")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r1 = await c.get("/test-decrement", headers=CLIENT_IP)
        r2 = await c.get("/test-decrement", headers=CLIENT_IP)

    assert int(r1.headers["X-RateLimit-Remaining"]) > int(
        r2.headers["X-RateLimit-Remaining"]
    )


# ── Decorator: 429 ────────────────────────────────────────────────────────────


async def test_decorator_returns_429_when_exceeded():
    app, _ = make_app()

    @app.get("/test-429")
    @rate_limit(limit=3, window=60, algorithm="fixed_window", key_by="ip")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(3):
            await c.get("/test-429", headers=CLIENT_IP)
        r = await c.get("/test-429", headers=CLIENT_IP)

    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "rate_limit_exceeded"
    assert "retry_after" in body
    assert "Retry-After" in r.headers


async def test_429_has_correct_limit_in_body():
    app, _ = make_app()

    @app.get("/test-429-body")
    @rate_limit(limit=2, window=60, algorithm="fixed_window", key_by="ip")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(2):
            await c.get("/test-429-body", headers=CLIENT_IP)
        r = await c.get("/test-429-body", headers=CLIENT_IP)

    assert r.status_code == 429
    assert r.json()["limit"] == 2


# ── key_by="ip" ───────────────────────────────────────────────────────────────


async def test_key_by_ip_different_ips_independent():
    app, _ = make_app()

    @app.get("/test-ip")
    @rate_limit(limit=2, window=60, algorithm="fixed_window", key_by="ip")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(2):
            await c.get("/test-ip", headers={"X-Forwarded-For": "10.0.0.1"})
        r_ip1 = await c.get("/test-ip", headers={"X-Forwarded-For": "10.0.0.1"})
        r_ip2 = await c.get("/test-ip", headers={"X-Forwarded-For": "10.0.0.2"})

    assert r_ip1.status_code == 429
    assert r_ip2.status_code == 200


# ── key_by="api_key" ──────────────────────────────────────────────────────────


async def test_key_by_api_key_independent_per_key():
    app, _ = make_app()

    @app.get("/test-apikey")
    @rate_limit(limit=2, window=60, algorithm="fixed_window", key_by="api_key")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(2):
            await c.get("/test-apikey", headers={**CLIENT_IP, "X-API-Key": "key-abc"})
        r_key1 = await c.get(
            "/test-apikey", headers={**CLIENT_IP, "X-API-Key": "key-abc"}
        )
        r_key2 = await c.get(
            "/test-apikey", headers={**CLIENT_IP, "X-API-Key": "key-xyz"}
        )

    assert r_key1.status_code == 429
    assert r_key2.status_code == 200


# ── key_by="user" ─────────────────────────────────────────────────────────────


async def test_key_by_user_independent_per_user():
    app, _ = make_app()

    @app.get("/test-user")
    @rate_limit(limit=2, window=60, algorithm="sliding_window", key_by="user")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(2):
            await c.get("/test-user", headers={**CLIENT_IP, "X-User-ID": "user-1"})
        r_u1 = await c.get("/test-user", headers={**CLIENT_IP, "X-User-ID": "user-1"})
        r_u2 = await c.get("/test-user", headers={**CLIENT_IP, "X-User-ID": "user-2"})

    assert r_u1.status_code == 429
    assert r_u2.status_code == 200


# ── Different routes are independent ─────────────────────────────────────────


async def test_different_routes_independent_limits():
    app, _ = make_app()

    @app.get("/route-a")
    @rate_limit(limit=2, window=60, algorithm="fixed_window", key_by="ip")
    async def route_a(request: Request):
        return JSONResponse(content={"route": "a"})

    @app.get("/route-b")
    @rate_limit(limit=2, window=60, algorithm="fixed_window", key_by="ip")
    async def route_b(request: Request):
        return JSONResponse(content={"route": "b"})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(2):
            await c.get("/route-a", headers=CLIENT_IP)
        r_a = await c.get("/route-a", headers=CLIENT_IP)
        r_b = await c.get("/route-b", headers=CLIENT_IP)

    assert r_a.status_code == 429
    assert r_b.status_code == 200


# ── Token bucket burst ────────────────────────────────────────────────────────


async def test_token_bucket_burst_via_decorator():
    app, _ = make_app()

    @app.get("/test-burst")
    @rate_limit(limit=5, window=60, algorithm="token_bucket", key_by="ip", burst=5)
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        results = [await c.get("/test-burst", headers=CLIENT_IP) for _ in range(10)]

    allowed = sum(1 for r in results if r.status_code == 200)
    assert allowed == 10


# ── All 4 algorithms via decorator ────────────────────────────────────────────


@pytest.mark.parametrize(
    "algorithm", ["fixed_window", "sliding_window", "token_bucket", "leaky_bucket"]
)
async def test_all_algorithms_via_decorator(algorithm):
    app, _ = make_app()
    limit = 5
    path = f"/test-algo-{algorithm}"

    @app.get(path)
    @rate_limit(
        limit=limit,
        window=60,
        algorithm=algorithm,
        key_by="ip",
        burst=0 if algorithm == "token_bucket" else None,
    )
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        results = [await c.get(path, headers=CLIENT_IP) for _ in range(limit + 3)]

    status_codes = [r.status_code for r in results]
    assert status_codes[:limit] == [200] * limit
    assert all(s == 429 for s in status_codes[limit:])


# ── Concurrent requests via decorator ─────────────────────────────────────────


async def test_concurrent_requests_via_decorator():
    app, _ = make_app()
    limit = 10

    @app.get("/test-concurrent")
    @rate_limit(limit=limit, window=60, algorithm="fixed_window", key_by="ip")
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        results = await asyncio.gather(
            *[c.get("/test-concurrent", headers=CLIENT_IP) for _ in range(20)]
        )

    allowed = sum(1 for r in results if r.status_code == 200)
    assert allowed == limit


# ── RateLimitMiddleware ───────────────────────────────────────────────────────


async def test_middleware_blocks_after_global_limit():
    backend = InMemoryBackend()
    mw_app = FastAPI()
    mw_app.state.backend = backend
    mw_app.state.fixed_window = FixedWindowAlgorithm(backend)
    mw_app.add_middleware(
        RateLimitMiddleware, limit=3, window=60, algorithm="fixed_window"
    )

    @mw_app.get("/resource")
    async def resource():
        return JSONResponse(content={"data": "ok"})

    async with AsyncClient(
        transport=ASGITransport(app=mw_app), base_url="http://test"
    ) as c:
        results = [await c.get("/resource", headers=CLIENT_IP) for _ in range(5)]

    codes = [r.status_code for r in results]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429
    assert codes[4] == 429


async def test_middleware_skips_health_endpoint():
    backend = InMemoryBackend()
    mw_app = FastAPI()
    mw_app.state.backend = backend
    mw_app.state.fixed_window = FixedWindowAlgorithm(backend)
    mw_app.add_middleware(
        RateLimitMiddleware, limit=1, window=60, algorithm="fixed_window"
    )

    @mw_app.get("/health")
    async def health():
        return JSONResponse(content={"status": "ok"})

    @mw_app.get("/data")
    async def data():
        return JSONResponse(content={"data": "ok"})

    async with AsyncClient(
        transport=ASGITransport(app=mw_app), base_url="http://test"
    ) as c:
        await c.get("/data", headers=CLIENT_IP)
        r_data = await c.get("/data", headers=CLIENT_IP)
        r_health = await c.get("/health", headers=CLIENT_IP)

    assert r_data.status_code == 429
    assert r_health.status_code == 200


# ── _rate_limit introspection ─────────────────────────────────────────────────


def test_decorator_stores_config_for_introspection():
    app = FastAPI()
    app.state.backend = InMemoryBackend()

    @app.get("/introspect")
    @rate_limit(
        limit=50, window=30, algorithm="token_bucket", key_by="api_key", burst=10
    )
    async def route(request: Request):
        return JSONResponse(content={"ok": True})

    cfg = route._rate_limit
    assert cfg["limit"] == 50
    assert cfg["window"] == 30
    assert cfg["algorithm"] == "token_bucket"
    assert cfg["key_by"] == "api_key"
    assert cfg["burst"] == 10
