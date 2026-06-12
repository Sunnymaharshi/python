import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from rate_limiter.algorithms.fixed_window import FixedWindowAlgorithm
from rate_limiter.algorithms.sliding_window import SlidingWindowAlgorithm
from rate_limiter.algorithms.token_bucket import TokenBucketAlgorithm
from rate_limiter.backends.memory import InMemoryBackend
from rate_limiter.backends.redis import RedisBackend
from rate_limiter.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── App state ─────────────────────────────────────────────────────────────────
backend: RedisBackend | InMemoryBackend | None = None
fixed_window: FixedWindowAlgorithm | None = None
sliding_window: SlidingWindowAlgorithm | None = None
token_bucket: TokenBucketAlgorithm | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Redis on startup, clean up on shutdown."""
    global backend, fixed_window, sliding_window, token_bucket

    logger.info("Connecting to Redis at %s", settings.redis_url)
    try:
        backend = RedisBackend(
            redis_url=settings.redis_url,
            max_connections=settings.redis_max_connections,
        )
        # Verify connection immediately — fail fast if Redis is down
        client = backend._client
        await client.ping()
        logger.info("Redis connection OK")
    except Exception as e:
        logger.warning("Redis unavailable (%s) — falling back to in-memory backend", e)
        backend = InMemoryBackend()

    fixed_window = FixedWindowAlgorithm(backend)
    sliding_window = SlidingWindowAlgorithm(backend)
    token_bucket = TokenBucketAlgorithm(backend)
    logger.info(
        "Rate limiter ready (algorithms: fixed_window, sliding_window, token_bucket)"
    )

    yield  # app runs here

    logger.info("Shutting down — closing backend")
    await backend.close()


app = FastAPI(
    title="API Rate Limiter",
    description="Production-grade rate limiter with 4 algorithms",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Helper: build rate limit headers ─────────────────────────────────────────
def rate_limit_headers(result) -> dict:
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_at),
    }
    if result.retry_after is not None:
        headers["Retry-After"] = str(result.retry_after)
    return headers


# ── Helper: extract rate limit key from request ───────────────────────────────
def get_client_key(request: Request, route: str) -> str:
    """
    Key identifies the caller + the route being accessed.
    Falls back to IP if no API key header is present.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        identifier = f"apikey:{api_key}"
    else:
        # Use real client IP (works behind a proxy via X-Forwarded-For)
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host
        identifier = f"ip:{ip}"

    return f"rl:fixed:{identifier}:{route}"


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "service": "API Rate Limiter",
        "algorithms": [
            "fixed_window",
            "sliding_window",
            "token_bucket",
            "leaky_bucket",
        ],
        "demo_endpoints": {
            "fixed_window": "/api/demo",
            "sliding_window": "/api/demo-sliding",
            "token_bucket": "/api/demo-token-bucket",
        },
        "docs": "/docs",
    }


@app.get("/api/demo")
async def demo(request: Request):
    """
    Demo endpoint protected by fixed window rate limiting.
    Default: 10 requests per 60 seconds per IP / API key.
    """
    key = get_client_key(request, "demo")
    limit = int(request.headers.get("X-Rate-Limit", "10"))
    window = int(request.headers.get("X-Rate-Window", "60"))

    result = await fixed_window.check(key=key, limit=limit, window=window)
    headers = rate_limit_headers(result)

    if not result.allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Try again in {result.retry_after}s.",
                "retry_after": result.retry_after,
            },
            headers=headers,
        )

    return JSONResponse(
        content={
            "message": "Request allowed",
            "algorithm": "fixed_window",
            "timestamp": int(time.time()),
            "rate_limit": {
                "limit": result.limit,
                "remaining": result.remaining,
                "reset_at": result.reset_at,
            },
        },
        headers=headers,
    )


@app.get("/api/demo-sliding")
async def demo_sliding(request: Request):
    """
    Demo endpoint protected by sliding window rate limiting.
    Same defaults as fixed window, but with perfect accuracy (no boundary burst).
    """
    key = get_client_key(request, "demo-sliding")
    limit = int(request.headers.get("X-Rate-Limit", "10"))
    window = int(request.headers.get("X-Rate-Window", "60"))

    result = await sliding_window.check(key=key, limit=limit, window=window)
    headers = rate_limit_headers(result)

    if not result.allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Try again in {result.retry_after}s.",
                "retry_after": result.retry_after,
            },
            headers=headers,
        )

    return JSONResponse(
        content={
            "message": "Request allowed",
            "algorithm": "sliding_window",
            "timestamp": int(time.time()),
            "rate_limit": {
                "limit": result.limit,
                "remaining": result.remaining,
                "reset_at": result.reset_at,
            },
        },
        headers=headers,
    )


@app.get("/api/demo-token-bucket")
async def demo_token_bucket(request: Request):
    """
    Demo endpoint protected by token bucket rate limiting.
    Allows configurable burst through X-Burst header.
    Default: 10 tokens capacity, 5 token burst allowance per 60 seconds.
    """
    key = get_client_key(request, "demo-token-bucket")
    limit = int(request.headers.get("X-Rate-Limit", "10"))
    window = int(request.headers.get("X-Rate-Window", "60"))
    burst = int(request.headers.get("X-Burst", str(limit // 2)))

    result = await token_bucket.check(key=key, limit=limit, window=window, burst=burst)
    headers = rate_limit_headers(result)

    if not result.allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded",
                "retry_after": f"{result.retry_after}s",
            },
            headers=headers,
        )

    return JSONResponse(
        content={
            "message": "Request allowed",
            "algorithm": "token_bucket",
            "timestamp": int(time.time()),
            "burst_allowance": burst,
            "rate_limit": {
                "limit": result.limit,
                "remaining": result.remaining,
                "reset_at": result.reset_at,
            },
        },
        headers=headers,
    )


@app.get("/health")
async def health():
    """Health check — also shows which backend is active."""
    backend_type = type(backend).__name__
    return {"status": "ok", "backend": backend_type}
