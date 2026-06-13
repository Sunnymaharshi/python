"""
Prometheus metrics for the rate limiter.

Exposes:
  rate_limiter_requests_total{algorithm, key_by, allowed}  — counter
  rate_limiter_request_duration_seconds{algorithm}         — histogram
"""

from fastapi import Request
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Histogram,
    generate_latest,
)


def _get_or_create(metric_class, name, doc, **kwargs):
    """
    Return existing collector if already registered, else create it.
    Prometheus stores Counter 'foo_total' under key 'foo' in the registry.
    We check both the bare name and the _total suffix to be safe.
    """
    for key in (name, name + "_total"):
        if key in REGISTRY._names_to_collectors:
            return REGISTRY._names_to_collectors[key]
    return metric_class(name, doc, **kwargs)


# ── Metrics ───────────────────────────────────────────────────────────────────

REQUESTS_TOTAL = _get_or_create(
    Counter,
    "rate_limiter_requests",
    "Total requests checked by the rate limiter",
    labelnames=["algorithm", "key_by", "allowed"],
)

REQUEST_DURATION = _get_or_create(
    Histogram,
    "rate_limiter_request_duration_seconds",
    "Time spent checking rate limit (seconds)",
    labelnames=["algorithm"],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
)


def record(algorithm: str, key_by: str, allowed: bool, duration: float) -> None:
    """Called by the decorator after every rate limit check."""
    try:
        REQUESTS_TOTAL.labels(
            algorithm=algorithm,
            key_by=key_by,
            allowed=str(allowed).lower(),
        ).inc()
        REQUEST_DURATION.labels(algorithm=algorithm).observe(duration)
    except Exception:
        pass  # never let metrics crash a request


async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics at GET /metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
