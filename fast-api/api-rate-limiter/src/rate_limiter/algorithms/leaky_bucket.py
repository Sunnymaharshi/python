"""
Leaky Bucket Rate Limiting
===========================

Starts empty. Fills on requests, drains at constant rate. No burst ever.
Strict, smooth output rate.

How it works:
  - Imagine a bucket with a hole at the bottom that leaks at a constant rate.
  - Requests are added to the bucket. If the bucket is full, requests are rejected.
  - The bucket drains at a fixed rate: `limit / window` requests per second.
  - This enforces a strict, constant output rate — no bursts allowed.

  constant output rate
    leak rate defines how many requests per second drain from the queue.
    At limit=10, window=60, the leak rate is 10/60 ≈ 0.167 req/sec,
    meaning one slot frees up roughly every 6 seconds.
    The math.floor is crucial — we only drain whole completed units, not fractional ones.
Redis implementation:
  - we only need 1 key per user & url, in redis
  - Track (queue_size, last_drain_time) to simulate the leak.
  - On each request: compute how much has drained since last request, decrement queue.
  - If queue < capacity: allow (queue++); otherwise reject.
  - Use Lua script for atomicity.

Tradeoff:
  ✓ Guarantees constant output rate (no spiky traffic)
  ✓ Smooth traffic distribution
  ✓ No bursts at all — strictly enforced
  ✗ More complex than fixed window
  ✗ Can feel overly restrictive (clients can't burst even briefly)

Key format: rl:leaky:{identifier}
  Value: "{queue_size}:{last_drain_time}" (e.g. "3:1234567890.1")

When to use:
  - Protecting backend services that can't handle spikes (databases, slow APIs)
  - Enforcing strict rate limits with no tolerance for bursts
  - When you need predictable, constant-rate output
  - Traffic shaping at network level

  Token bucket vs Leaky bucket
    Token bucket
        starts with full capacity
        On request consume a token
        Burst allowed
    Leaky bucket
        starts with Empty (queue is empty)
        On request add to queue
        Burst never

"""

import math
import time

from rate_limiter.backends.base import BaseBackend

from .base import BaseAlgorithm, RateLimitResult


class LeakyBucketAlgorithm(BaseAlgorithm):
    def __init__(self, backend: BaseBackend) -> None:
        super().__init__(backend)

    async def check(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        """
        Check if a request is allowed under leaky bucket rules.

        Args:
            key: identifier for rate limit (e.g. "rl:leaky:user:123:/api/data")
            limit: max requests per window (e.g. 100 per 60s)
            window: window size in seconds (e.g. 60)

        Returns:
            RateLimitResult with allowed, remaining, reset_at, retry_after
        """
        now = time.time()
        capacity = float(limit)
        leak_rate = capacity / float(window)  # requests per second that drain

        # Execute the leaky bucket Lua script atomically
        result = await self.backend.execute_lua(
            script="""
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local leak_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            -- Get current state or initialize
            local state = redis.call('GET', key)
            local queue_size, last_drain
            
            if state == false then
              queue_size = 0
              last_drain = now
            else
              local parts = {}
              for part in string.gmatch(state, '[^:]+') do
                table.insert(parts, part)
              end
              queue_size = tonumber(parts[1])
              last_drain = tonumber(parts[2])
            end
            
            -- Calculate how much has drained since last request
            local elapsed = now - last_drain
            local drained = math.floor(elapsed * leak_rate)
            
            -- CRITICAL: Instead of setting last_drain = now, 
            -- we calculate exactly how long it took to drain whole units (drained/leak_rate)
            -- and add only that amount to our baseline timer.
            -- This preserves the partial time accumulated toward the next drain slot.
            -- e.g. leak_rate=0.167/s, elapsed=3.5s → drained=0, last_drain unchanged
            --      → the 3.5s keeps accumulating toward the next whole unit (6s threshold)
            if drained > 0 then
              queue_size = math.max(0, queue_size - drained)
              last_drain = last_drain + (drained / leak_rate)
            end
            
            -- If bucket fully drained, reset last_drain to now.
            -- Prevents float drift after long idle periods.
            if queue_size == 0 then
              last_drain = now
            end
            
            -- Check if we can add this request to the queue
            local allowed = 0
            if queue_size < capacity then
              allowed = 1
              queue_size = queue_size + 1
            end
            
            -- Save state
            local ttl = math.ceil((capacity / leak_rate) + 10)
            redis.call('SET', key, queue_size .. ':' .. last_drain, 'EX', ttl)
            
            -- Return [allowed, queue_size_after, last_drain_as_string].
            -- last_drain lets Python compute precise retry_after, accounting
            -- for partial progress already made toward the next drain tick.
            return {allowed, math.floor(queue_size), tostring(last_drain)}
            """,
            keys=[key],
            args=[str(capacity), str(leak_rate), str(now)],
        )

        allowed = bool(result[0])
        queue_size = int(result[1])
        last_drain = float(result[2])

        # remaining = available slots in the bucket
        remaining = max(0, int(capacity) - queue_size)

        # reset_at: when the queue will be fully empty again (all slots free),
        # assuming no further requests arrive.
        if queue_size <= 0:
            reset_at = int(now)
        else:
            time_to_drain = queue_size / leak_rate
            reset_at = int(now + time_to_drain)

        retry_after = None
        if not allowed:
            # Time until the NEXT single slot frees up.
            # last_drain marks when the drain clock last ticked over a whole
            # unit; (now - last_drain) is partial progress already made
            # toward the next tick. The remaining time for that tick is:
            #   (1 / leak_rate) - (now - last_drain)
            elapsed_since_drain = now - last_drain
            time_per_slot = 1.0 / leak_rate
            remaining_time = time_per_slot - elapsed_since_drain
            retry_after = max(1, math.ceil(remaining_time))

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )
