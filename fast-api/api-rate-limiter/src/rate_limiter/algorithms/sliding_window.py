"""
Sliding Window Log Rate Limiting
==================================

How it works:
  - Store a timestamp for every request in a Redis sorted set.
  - To check a new request: count how many timestamps fall within the last `window` seconds.
  - If count >= limit, reject. Otherwise accept and add this request's timestamp.
  - To check a new request, you count how many timestamps fall within the last 60 seconds.
  - If the count is below the limit, allow it and record the new timestamp.

    On every request
        Remove old timestamps
        Count remaining
        Check limit
    We use sorted sets
        because range queries on unsorted data are O(N).
        Sorted sets are the perfect data structure here.
Tradeoff:
  ✓ Perfect accuracy — no boundary burst like fixed window
  ✓ True rolling window — a client can't cheat the boundary
  ✗ Memory-heavy — stores every request timestamp, not just a counter
  ✗ More Redis calls per request (4 vs 2 in fixed window)

When to use:
  - When you absolutely cannot allow boundary bursts
  - When request volume is low (< 1000 req/window)
  - When accuracy is more important than performance
"""

import time

from rate_limiter.backends.base import BaseBackend

from .base import BaseAlgorithm, RateLimitResult


class SlidingWindowAlgorithm(BaseAlgorithm):
    def __init__(self, backend: BaseBackend) -> None:
        super().__init__(backend)

    async def check(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        now = time.time()
        window_start = now - window

        # Use sorted set methods if available (memory backend or extended Redis)
        if hasattr(self.backend, "zremrangebyscore"):
            # 1. Remove all timestamps older than the current window
            await self.backend.zremrangebyscore(key, float("-inf"), window_start)

            # 2. Count requests still within the window
            count = await self.backend.zcard(key)

            # 3. Check if we allow this request
            allowed = count < limit

            if allowed:
                # Add this request's timestamp to the sorted set
                await self.backend.zadd(key, now, str(now))
                remaining = limit - count - 1
            else:
                remaining = 0
        else:
            # Fallback for backends without sorted set methods
            allowed = False
            remaining = 0

        # Determine reset time (when the oldest request in the window expires)
        reset_at = int(now + window)
        retry_after = (window + 1) if not allowed else None

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )
