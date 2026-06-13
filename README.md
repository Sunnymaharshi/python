# API Rate Limiter

A production-grade rate limiting library built with FastAPI and Redis. Implements 4 algorithms as pluggable FastAPI middleware, backed by atomic Redis Lua scripts to guarantee correctness under concurrent load.

## Features

- **4 algorithms** — Fixed Window, Sliding Window, Token Bucket, Leaky Bucket
- **Pluggable backends** — Redis (production), In-Memory (tests/dev)
- **One-line decorator** — `@rate_limit(limit=100, window=60, algorithm="token_bucket")`
- **Per-IP, per-API-key, per-user** scoping
- **Atomic under concurrency** — Redis Lua scripts, no race conditions
- **Standard HTTP headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- **Prometheus metrics** — `/metrics` endpoint with request counters and latency histograms
- **IP whitelist** — bypass rate limiting for trusted callers

## Quick Start

```bash
# Start the server + Redis
docker compose up --build

# Try it
curl http://localhost:8000/api/token
curl http://localhost:8000/metrics
```

## Usage

```python
from rate_limiter.middleware.rate_limit import rate_limit

# Per-IP, token bucket with burst
@app.get("/api/data")
@rate_limit(limit=100, window=60, algorithm="token_bucket", key_by="ip", burst=20)
async def my_route(request: Request):
    return {"data": "..."}

# Per-API-key, sliding window (no boundary burst)
@app.get("/api/write")
@rate_limit(limit=10, window=60, algorithm="sliding_window", key_by="api_key")
async def write_route(request: Request):
    return {"ok": True}

# Per-user, leaky bucket (strict constant rate)
@app.get("/api/action")
@rate_limit(limit=5, window=60, algorithm="leaky_bucket", key_by="user")
async def action_route(request: Request):
    return {"queued": True}
```

**Global middleware** (applies to all routes):

```python
app.add_middleware(RateLimitMiddleware, limit=1000, window=60, algorithm="fixed_window")
```

## Algorithms

| Algorithm      | Memory                   | Burst                   | Use when                           |
| -------------- | ------------------------ | ----------------------- | ---------------------------------- |
| Fixed Window   | Very low                 | Boundary burst possible | Internal APIs, high traffic        |
| Sliding Window | High (1 key per request) | None                    | Auth endpoints, financial APIs     |
| Token Bucket   | Low                      | Configurable            | Public APIs, smoothing spikes      |
| Leaky Bucket   | Low                      | None                    | Protecting slow downstream systems |

### Fixed Window

Divides time into fixed-size buckets. Counter resets at each boundary. Fast (1–2 Redis ops) but allows 2× limit at window edges.

```
Key: rl:fixed:ip:1.2.3.4:/api/data:1718000000
Value: counter (integer)
Ops: INCR + EXPIRE (on first request only)
```

### Sliding Window Log

Stores every request timestamp in a Redis sorted set. Rolling window with perfect accuracy — no boundary burst possible.

```
Key: rl:sliding:ip:1.2.3.4:/api/data
Value: sorted set of timestamps
Ops: ZREMRANGEBYSCORE + ZCARD + ZADD + EXPIRE
```

### Token Bucket

Tokens refill at a constant rate. Allows brief bursts up to `capacity + burst`. Uses an atomic Lua script to prevent race conditions.

```
Key: rl:token:ip:1.2.3.4:/api/data
Value: "tokens:last_refill_time"
Ops: GET + Lua (refill, check, SET) — atomic
```

### Leaky Bucket

Models a queue that drains at a constant rate. Requests are admitted until the queue is full. No burst allowed.

```
Key: rl:leaky:ip:1.2.3.4:/api/data
Value: "queue_size:last_drain_time"
Ops: GET + Lua (drain, check, SET) — atomic
```

## HTTP Headers

Every response includes:

```
X-RateLimit-Limit: 100          # total requests allowed per window
X-RateLimit-Remaining: 42       # requests left in current window
X-RateLimit-Reset: 1718000060   # unix timestamp when window resets
Retry-After: 15                 # seconds until next request allowed (on 429 only)
```

## Configuration

Via environment variables or `.env` file:

```env
REDIS_URL=redis://localhost:6379/0
DEFAULT_REQUESTS=100
DEFAULT_WINDOW_SECONDS=60
DEFAULT_ALGORITHM=token_bucket
WHITELISTED_IPS=127.0.0.1,::1,10.0.0.0/8
METRICS_ENABLED=true
```

## Running Tests

```bash
# All 64 unit tests
uv run pytest tests/unit/ -v

# Concurrent correctness tests only
uv run pytest tests/unit/test_concurrent.py -v

# Load test (requires running server)
docker compose up -d
uv run locust -f tests/load/locustfile.py --headless \
    -u 50 -r 10 -t 30s --host http://localhost:8000 \
    --html tests/load/report.html
```

## Architecture

```
src/rate_limiter/
├── config.py               # Settings via pydantic-settings
├── main.py                 # FastAPI app + demo routes
├── algorithms/
│   ├── base.py             # RateLimitResult + BaseAlgorithm
│   ├── fixed_window.py     # INCR + EXPIRE
│   ├── sliding_window.py   # Sorted set (ZADD/ZCARD/ZREMRANGEBYSCORE)
│   ├── token_bucket.py     # Lua: refill on elapsed time, allow/consume
│   └── leaky_bucket.py     # Lua: drain on elapsed time, queue/reject
├── backends/
│   ├── base.py             # Abstract interface
│   ├── redis.py            # Production (redis.asyncio + hiredis)
│   └── memory.py           # Tests/dev (asyncio.Lock)
├── middleware/
│   └── rate_limit.py       # @rate_limit decorator + RateLimitMiddleware
└── api/
    └── metrics.py          # Prometheus counters + histograms
```

## Concurrency Design

The critical correctness property: under N concurrent requests, exactly `limit` are allowed and `N - limit` are denied — no over-admission.

**Fixed Window** uses Redis `INCR` which is atomic by definition. Multiple concurrent requests each get a unique monotonically increasing count back. No Lua needed.

**Sliding Window** relies on the sequence `ZREMRANGEBYSCORE → ZCARD → ZADD` running in the right order. The in-memory backend uses `asyncio.Lock` to serialize. In production Redis this is safe because individual commands are atomic and the sequence is fast enough that the window doesn't shift meaningfully between ops.

**Token Bucket and Leaky Bucket** both use Lua scripts via `EVAL`. Redis executes Lua atomically — the entire script runs before any other command is processed. This makes the read-compute-write cycle race-condition-free regardless of concurrency.

## Prometheus Metrics

```
# Requests by algorithm and outcome
rate_limiter_requests_total{algorithm="token_bucket",key_by="ip",allowed="true"} 1523
rate_limiter_requests_total{algorithm="token_bucket",key_by="ip",allowed="false"} 477

# Latency histogram
rate_limiter_request_duration_seconds_bucket{algorithm="token_bucket",le="0.001"} 1891
```
