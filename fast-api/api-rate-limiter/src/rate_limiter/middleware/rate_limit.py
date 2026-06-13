"""
@rate_limit decorator + RateLimitMiddleware
============================================

Usage — decorator on any route:

    @app.get("/api/data")
    @rate_limit(limit=100, window=60, algorithm="token_bucket", key_by="ip")
    async def my_route(request: Request):
        return {"data": "..."}

    @app.get("/api/write")
    @rate_limit(limit=10, window=60, algorithm="sliding_window", key_by="user", burst=0)
    async def write_route(request: Request):
        return {"ok": True}

key_by options:
    "ip"      — rate limit per client IP (via X-Forwarded-For or request.client.host)
    "api_key" — rate limit per X-API-Key header value
    "user"    — rate limit per X-User-ID header value (set by your auth middleware)

The decorator injects rate limit headers into every response:
    X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After
"""

import functools
import logging
import time as _time
from typing import Literal

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

AlgorithmName = Literal[
    "fixed_window", "sliding_window", "token_bucket", "leaky_bucket"
]
KeyBy = Literal["ip", "api_key", "user"]


def _extract_key(request: Request, key_by: KeyBy) -> str:
    """
    Build a rate limit identifier from the request.
    Falls back gracefully if the expected header is missing.
    """
    if key_by == "api_key":
        value = request.headers.get("X-API-Key", "")
        return f"apikey:{value}" if value else _ip_key(request)

    if key_by == "user":
        value = request.headers.get("X-User-ID", "")
        return f"user:{value}" if value else _ip_key(request)

    return _ip_key(request)


def _ip_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    return f"ip:{ip}"


def _is_whitelisted(request: Request) -> bool:
    """Skip rate limiting entirely for whitelisted IPs."""
    from rate_limiter.config import settings

    forwarded = request.headers.get("X-Forwarded-For")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "")
    )
    return ip in settings.whitelisted_ips


def _build_headers(result) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_at),
    }
    if result.retry_after is not None:
        headers["Retry-After"] = str(result.retry_after)
    return headers


def _get_algorithm(request: Request, algorithm: AlgorithmName):
    """Fetch the algorithm instance from app.state."""
    state = request.app.state
    mapping = {
        "fixed_window": getattr(state, "fixed_window", None),
        "sliding_window": getattr(state, "sliding_window", None),
        "token_bucket": getattr(state, "token_bucket", None),
        "leaky_bucket": getattr(state, "leaky_bucket", None),
    }
    algo = mapping.get(algorithm)
    if algo is None:
        raise RuntimeError(
            f"Algorithm '{algorithm}' not found on app.state. "
            "Did you initialise algorithms in lifespan()?"
        )
    return algo


def rate_limit(
    limit: int,
    window: int,
    algorithm: AlgorithmName = "token_bucket",
    key_by: KeyBy = "ip",
    burst: int | None = None,
):
    """
    Decorator that applies rate limiting to a FastAPI route.

    Args:
        limit:     max requests allowed per window
        window:    window size in seconds
        algorithm: which algorithm to use
        key_by:    how to identify the caller ("ip", "api_key", "user")
        burst:     token bucket only — extra burst allowance on top of limit

    Example:
        @app.get("/api/data")
        @rate_limit(limit=100, window=60, algorithm="token_bucket", key_by="ip")
        async def my_route(request: Request):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Whitelist check — bypass entirely for trusted IPs
            if _is_whitelisted(request):
                return await func(request, *args, **kwargs)

            # Build scoped key: algorithm + caller identity + route path
            caller_key = _extract_key(request, key_by)
            route_path = request.url.path.replace("/", "_")
            rl_key = f"rl:{algorithm}:{caller_key}:{route_path}"

            # Run the check + time it for Prometheus
            algo = _get_algorithm(request, algorithm)
            t0 = _time.monotonic()

            if algorithm == "token_bucket":
                result = await algo.check(
                    key=rl_key,
                    limit=limit,
                    window=window,
                    burst=burst,
                )
            else:
                result = await algo.check(
                    key=rl_key,
                    limit=limit,
                    window=window,
                )

            duration = _time.monotonic() - t0

            # Record to Prometheus (import lazily so metrics module is optional)
            try:
                from rate_limiter.api.metrics import record as _record
                from rate_limiter.config import settings

                if settings.metrics_enabled:
                    _record(algorithm, key_by, result.allowed, duration)
            except Exception:
                pass  # never let metrics crash the request

            headers = _build_headers(result)

            if not result.allowed:
                logger.warning(
                    "Rate limit exceeded | algo=%s key=%s limit=%d",
                    algorithm,
                    caller_key,
                    limit,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Too many requests. Try again in {result.retry_after}s.",
                        "retry_after": result.retry_after,
                        "limit": result.limit,
                    },
                    headers=headers,
                )

            # Call the actual route handler
            response = await func(request, *args, **kwargs)

            # Inject rate limit headers into successful response
            for k, v in headers.items():
                response.headers[k] = v

            return response

        # Store rate limit config on the wrapper for introspection / testing
        wrapper._rate_limit = {
            "limit": limit,
            "window": window,
            "algorithm": algorithm,
            "key_by": key_by,
            "burst": burst,
        }
        return wrapper

    return decorator


class RateLimitMiddleware:
    """
    Optional ASGI (Asynchronous Server Gateway Interface) middleware
    applies a global default rate limit to ALL routes.
    Use this when you want a blanket limit in addition to per-route decorators,
    or when you can't modify individual route handlers.

    Add to app:
        app.add_middleware(RateLimitMiddleware, limit=1000, window=60)
    """

    def __init__(
        self,
        app,
        limit: int = 1000,
        window: int = 60,
        algorithm: AlgorithmName = "fixed_window",
    ):
        self.app = app
        self.limit = limit
        self.window = window
        self.algorithm = algorithm

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip health + docs endpoints
        if request.url.path in ("/health", "/docs", "/openapi.json", "/"):
            await self.app(scope, receive, send)
            return

        if _is_whitelisted(request):
            await self.app(scope, receive, send)
            return

        # Get algorithm from app state
        try:
            algo = _get_algorithm(request, self.algorithm)
        except RuntimeError:
            await self.app(scope, receive, send)
            return

        caller_key = _ip_key(request)
        rl_key = f"rl:global:{self.algorithm}:{caller_key}"

        result = await algo.check(
            key=rl_key,
            limit=self.limit,
            window=self.window,
        )

        if not result.allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Global rate limit exceeded. Try again in {result.retry_after}s.",
                    "retry_after": result.retry_after,
                },
                headers=_build_headers(result),
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
