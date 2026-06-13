import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from rate_limiter.algorithms.fixed_window import FixedWindowAlgorithm
from rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from rate_limiter.algorithms.sliding_window import SlidingWindowAlgorithm
from rate_limiter.algorithms.token_bucket import TokenBucketAlgorithm
from rate_limiter.api.metrics import metrics_endpoint
from rate_limiter.backends.memory import InMemoryBackend
from rate_limiter.backends.redis import RedisBackend
from rate_limiter.config import settings
from rate_limiter.middleware.rate_limit import rate_limit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Redis on startup, store algorithms on app.state."""
    logger.info("Connecting to Redis at %s", settings.redis_url)
    try:
        backend = RedisBackend(
            redis_url=settings.redis_url,
            max_connections=settings.redis_max_connections,
        )
        await backend._client.ping()
        logger.info("Redis connection OK")
    except Exception as e:
        logger.warning("Redis unavailable (%s) — falling back to in-memory backend", e)
        backend = InMemoryBackend()

    # Store on app.state so decorator + middleware can find them
    app.state.backend = backend
    app.state.fixed_window = FixedWindowAlgorithm(backend)
    app.state.sliding_window = SlidingWindowAlgorithm(backend)
    app.state.token_bucket = TokenBucketAlgorithm(backend)
    app.state.leaky_bucket = LeakyBucketAlgorithm(backend)
    logger.info("Rate limiter ready — all 4 algorithms loaded")

    yield

    logger.info("Shutting down — closing backend")
    await backend.close()


app = FastAPI(
    title="API Rate Limiter",
    description="Production-grade rate limiter — 4 algorithms, Redis backend, FastAPI middleware",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Routes ─────────────────────────────────────────────────────────────────────


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
            "fixed_window": "/api/fixed",
            "sliding_window": "/api/sliding",
            "token_bucket": "/api/token",
            "leaky_bucket": "/api/leaky",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health(request: Request):
    backend_type = type(request.app.state.backend).__name__
    return {"status": "ok", "backend": backend_type}


@app.get("/metrics")
async def metrics(request: Request):
    """Prometheus metrics endpoint."""
    return await metrics_endpoint(request)


# ── Demo routes — one decorator line each ─────────────────────────────────────


@app.get("/api/fixed")
@rate_limit(limit=10, window=60, algorithm="fixed_window", key_by="ip")
async def demo_fixed(request: Request):
    return JSONResponse(
        content={
            "message": "Request allowed",
            "algorithm": "fixed_window",
            "timestamp": int(time.time()),
        }
    )


@app.get("/api/sliding")
@rate_limit(limit=10, window=60, algorithm="sliding_window", key_by="ip")
async def demo_sliding(request: Request):
    return JSONResponse(
        content={
            "message": "Request allowed",
            "algorithm": "sliding_window",
            "timestamp": int(time.time()),
        }
    )


@app.get("/api/token")
@rate_limit(limit=10, window=60, algorithm="token_bucket", key_by="ip", burst=5)
async def demo_token(request: Request):
    return JSONResponse(
        content={
            "message": "Request allowed",
            "algorithm": "token_bucket",
            "timestamp": int(time.time()),
        }
    )


@app.get("/api/leaky")
@rate_limit(limit=10, window=60, algorithm="leaky_bucket", key_by="ip")
async def demo_leaky(request: Request):
    return JSONResponse(
        content={
            "message": "Request allowed",
            "algorithm": "leaky_bucket",
            "timestamp": int(time.time()),
        }
    )


# ── Per-API-key route ──────────────────────────────────────────────────────────


@app.get("/api/premium")
@rate_limit(
    limit=1000, window=60, algorithm="token_bucket", key_by="api_key", burst=200
)
async def premium_endpoint(request: Request):
    """Higher limit, burst allowed — typical for paid API tiers."""
    return JSONResponse(
        content={
            "message": "Premium request allowed",
            "algorithm": "token_bucket",
            "key_by": "api_key",
            "timestamp": int(time.time()),
        }
    )


# ── Per-user route ─────────────────────────────────────────────────────────────


@app.get("/api/user-action")
@rate_limit(limit=5, window=60, algorithm="sliding_window", key_by="user")
async def user_action(request: Request):
    """Strict per-user limit — e.g. for write operations."""
    return JSONResponse(
        content={
            "message": "User action allowed",
            "algorithm": "sliding_window",
            "key_by": "user",
            "timestamp": int(time.time()),
        }
    )
