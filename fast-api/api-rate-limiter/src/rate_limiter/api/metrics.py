"""
Prometheus metrics for the rate limiter.

Exposes:
  rate_limiter_requests_total{algorithm, key_by, allowed}  — counter
  rate_limiter_request_duration_seconds{algorithm}         — histogram

Mount at /metrics via the FastAPI app.
"""

from fastapi import Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# ── Metrics ───────────────────────────────────────────────────────────────────

REQUESTS_TOTAL = Counter(
    "rate_limiter_requests_total",
    "Total requests checked by the rate limiter",
    labelnames=["algorithm", "key_by", "allowed"],
)

REQUEST_DURATION = Histogram(
    "rate_limiter_request_duration_seconds",
    "Time spent checking rate limit (seconds)",
    labelnames=["algorithm"],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
)


def record(algorithm: str, key_by: str, allowed: bool, duration: float) -> None:
    """Called by the decorator after every rate limit check."""
    REQUESTS_TOTAL.labels(
        algorithm=algorithm,
        key_by=key_by,
        allowed=str(allowed).lower(),
    ).inc()
    REQUEST_DURATION.labels(algorithm=algorithm).observe(duration)


async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics at GET /metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
