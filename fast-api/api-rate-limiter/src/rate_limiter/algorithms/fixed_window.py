"""
Fixed Window Rate Limiting
==========================

How it works:
  - Time is divided into fixed-size buckets (e.g. every 60 seconds).
  - Each bucket has a counter. Requests increment the counter.
  - If counter > limit, the request is rejected until the window expires.

  key design
    rl:fixed:ip:192.168.1.1:/api/demo:1718000000
    rl:fixed:ip:192.168.1.1:/api/demo:1718000060   ← next window

  When the TTL expires Redis deletes the key automatically. No cleanup job needed.

Redis operations:
  1. INCR key          → atomically increment counter (creates at 0 if missing)
  2. EXPIRE key window → set TTL on first write only (so the window auto-expires)

The INCR+EXPIRE pair is NOT atomic — there's a tiny race window where two
concurrent requests both see count=1 and both call EXPIRE, but that's harmless
(they'll set the same TTL). The counter itself is always correct because INCR
is atomic.

Tradeoff:
  ✓ Extremely simple and fast — just one INCR + conditional EXPIRE
  ✓ Very low memory — one key per (identifier, window)
  ✗ Boundary burst problem:
        a client can make 2X the limit by hitting the end of one window and
        the start of the next back-to-back.
        59s | 00s
        10 req  10 req = 20 requests in 2 seconds
    Use sliding window if you need to prevent that.

Key format: rl:fixed:{identifier}:{window_start_unix}
"""

import time

from ..backends.base import BaseBackend
from .base import BaseAlgorithm, RateLimitResult


class FixedWindowAlgorithm(BaseAlgorithm):
    def __init__(self, backend: BaseBackend) -> None:
        super().__init__(backend)

    async def check(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        now = int(time.time())

        # Which window bucket are we in right now?
        window_start = (now // window) * window
        window_end = window_start + window

        # Scoped key: includes the window start so each bucket is independent
        window_key = f"{key}:{window_start}"

        # --- Core logic: two Redis calls ---

        # 1. Atomically increment. Returns the new count after increment.
        #    If the key doesn't exist, Redis creates it at 0 then increments → 1.
        count = await self.backend.incr(window_key)

        # 2. Set expiry only on the first request in this window.
        #    On subsequent requests the key already has a TTL, so we skip the call.
        #    We add +1 second as a small buffer so Redis doesn't evict the key
        #    before the window is fully over.
        if count == 1:
            await self.backend.expire(window_key, window + 1)

        # --- Build the result ---
        allowed = count <= limit
        remaining = max(0, limit - count)
        retry_after = (window_end - now) if not allowed else None

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_at=window_end,
            retry_after=retry_after,
        )
