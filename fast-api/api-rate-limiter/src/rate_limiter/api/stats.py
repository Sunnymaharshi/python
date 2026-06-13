"""
/api/stats — JSON endpoint polled by the dashboard every 2 seconds.

Reads directly from the Prometheus registry in-process.
No external Prometheus server needed.
"""

from prometheus_client import REGISTRY


def _get_stats() -> dict:
    algorithms = ["fixed_window", "sliding_window", "token_bucket", "leaky_bucket"]

    allowed_counts = {a: 0 for a in algorithms}
    denied_counts = {a: 0 for a in algorithms}
    # histogram: algo -> list of (le_float, cumulative_count)
    hist_buckets: dict[str, list[tuple[float, int]]] = {a: [] for a in algorithms}
    hist_counts: dict[str, int] = {a: 0 for a in algorithms}

    for metric in REGISTRY.collect():
        # Counter name: prometheus stores as "rate_limiter_requests"
        # but samples come out as "rate_limiter_requests_total"
        if metric.name == "rate_limiter_requests":
            for sample in metric.samples:
                if not sample.name.endswith("_total"):
                    continue
                algo = sample.labels.get("algorithm", "")
                allowed = sample.labels.get("allowed", "")
                if algo not in algorithms:
                    continue
                if allowed == "true":
                    allowed_counts[algo] += int(sample.value)
                elif allowed == "false":
                    denied_counts[algo] += int(sample.value)

        elif metric.name == "rate_limiter_request_duration_seconds":
            for sample in metric.samples:
                algo = sample.labels.get("algorithm", "")
                if algo not in algorithms:
                    continue
                if sample.name.endswith("_bucket"):
                    le = sample.labels.get("le", "")
                    if le != "+Inf":
                        hist_buckets[algo].append((float(le), int(sample.value)))
                elif sample.name.endswith("_count"):
                    hist_counts[algo] = int(sample.value)

    result = {}
    for algo in algorithms:
        total = allowed_counts[algo] + denied_counts[algo]
        allowed = allowed_counts[algo]
        denied = denied_counts[algo]
        throttle_rate = round(denied / total * 100, 1) if total > 0 else 0.0
        p99 = _approx_percentile(hist_buckets[algo], 0.99, hist_counts[algo])

        result[algo] = {
            "allowed": allowed,
            "denied": denied,
            "total": total,
            "throttle_rate": throttle_rate,
            "p99_ms": round(p99 * 1000, 2),
        }

    return {
        "algorithms": result,
        "total_requests": sum(v["total"] for v in result.values()),
        "total_allowed": sum(v["allowed"] for v in result.values()),
        "total_denied": sum(v["denied"] for v in result.values()),
    }


def _approx_percentile(buckets: list[tuple[float, int]], p: float, total: int) -> float:
    if not buckets or total == 0:
        return 0.0
    target = p * total
    prev_count = 0
    prev_le = 0.0
    for le, count in sorted(buckets):
        if count >= target:
            if count == prev_count:
                return le
            frac = (target - prev_count) / (count - prev_count)
            return prev_le + frac * (le - prev_le)
        prev_count = count
        prev_le = le
    return prev_le
