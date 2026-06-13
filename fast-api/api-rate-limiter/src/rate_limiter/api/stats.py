"""
/api/stats — JSON endpoint polled by the dashboard every 2 seconds.

Returns per-algorithm allowed/denied counts and latency percentiles
by reading directly from the Prometheus registry in-process.
No external Prometheus server needed.
"""

from prometheus_client import REGISTRY


def _get_stats() -> dict:
    """
    Walk the Prometheus registry and extract rate limiter metrics.
    Returns a dict ready to JSON-serialize for the dashboard.
    """
    algorithms = ["fixed_window", "sliding_window", "token_bucket", "leaky_bucket"]

    allowed_counts = {a: 0 for a in algorithms}
    denied_counts = {a: 0 for a in algorithms}
    durations = {a: [] for a in algorithms}  # list of (le, count) for histograms

    for metric in REGISTRY.collect():
        if metric.name == "rate_limiter_requests_total":
            for sample in metric.samples:
                algo = sample.labels.get("algorithm", "")
                allowed = sample.labels.get("allowed", "")
                if algo in algorithms:
                    if allowed == "true":
                        allowed_counts[algo] += int(sample.value)
                    elif allowed == "false":
                        denied_counts[algo] += int(sample.value)

        elif metric.name == "rate_limiter_request_duration_seconds":
            for sample in metric.samples:
                if sample.name.endswith("_bucket"):
                    algo = sample.labels.get("algorithm", "")
                    le = sample.labels.get("le", "")
                    if algo in algorithms and le != "+Inf":
                        durations[algo].append((float(le), int(sample.value)))

    # Build per-algorithm summary
    result = {}
    for algo in algorithms:
        total = allowed_counts[algo] + denied_counts[algo]
        allowed = allowed_counts[algo]
        denied = denied_counts[algo]
        throttle_rate = round((denied / total * 100), 1) if total > 0 else 0.0

        # Approximate p99 from histogram buckets
        p99 = _approx_percentile(durations[algo], 0.99, total)

        result[algo] = {
            "allowed": allowed,
            "denied": denied,
            "total": total,
            "throttle_rate": throttle_rate,  # % of requests denied
            "p99_ms": round(p99 * 1000, 2),
        }

    return {
        "algorithms": result,
        "total_requests": sum(v["total"] for v in result.values()),
        "total_allowed": sum(v["allowed"] for v in result.values()),
        "total_denied": sum(v["denied"] for v in result.values()),
    }


def _approx_percentile(buckets: list[tuple[float, int]], p: float, total: int) -> float:
    """Approximate a percentile from histogram bucket counts."""
    if not buckets or total == 0:
        return 0.0
    target = p * total
    prev_count = 0
    prev_le = 0.0
    for le, count in sorted(buckets):
        if count >= target:
            # Linear interpolation within this bucket
            if count == prev_count:
                return le
            frac = (target - prev_count) / (count - prev_count)
            return prev_le + frac * (le - prev_le)
        prev_count = count
        prev_le = le
    return prev_le
