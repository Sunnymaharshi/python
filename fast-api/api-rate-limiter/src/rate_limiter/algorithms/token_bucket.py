"""
Token Bucket Rate Limiting
===========================

How it works:
  - Imagine a bucket that holds up to `capacity` tokens.
  - Tokens refill at a constant rate: `capacity / window` tokens per second.
  - Every request consumes 1 token.
  - If tokens >= requested: allow and consume; otherwise reject.
  - You can optionally allow brief bursts on top of `capacity` via `burst`
    (the bucket can hold up to `capacity + burst` tokens, and a brand-new
    bucket starts completely full at that amount).

Redis implementation:
  - Store (tokens, last_refill_time) as a single string: "tokens:timestamp"
  - On each request: compute elapsed time, refill tokens, then check/consume
  - Use a Lua script to make this atomic — no race conditions

Tradeoff:
  ✓ Allows configurable bursts — smooth out traffic spikes
  ✓ Guarantees long-term rate (avg tokens/sec stays constant)
  ✓ More intuitive than sliding window for smoothing traffic
  ✗ Slightly more complex than fixed window
  ✗ Burst allowance can be confusing to tune

Key format: rl:token:{identifier}
  Value: "{tokens}:{last_refill_time}" (e.g. "45.5:1234567890.1")

When to use:
  - APIs that can handle brief spikes but must limit sustained load
  - Load balancing — smooth incoming traffic
  - When you want to allow users to "bank" requests (burst allowance)
"""

import math
import time

from rate_limiter.backends.base import BaseBackend

from .base import BaseAlgorithm, RateLimitResult


class TokenBucketAlgorithm(BaseAlgorithm):
    def __init__(self, backend: BaseBackend) -> None:
        super().__init__(backend)

    async def check(
        self,
        key: str,
        limit: int,
        window: int,
        burst: int | None = None,
    ) -> RateLimitResult:
        """
        Check if a request is allowed under token bucket rules.

        Args:
            key: identifier for rate limit (e.g. "rl:token:user:123:/api/data")
            limit: max requests per window (e.g. 100 per 60s). Must be > 0.
            window: window size in seconds (e.g. 60). Must be > 0.
            burst: optional burst allowance in tokens (default = limit).
                   If set, the bucket can hold up to capacity + burst tokens,
                   and a brand-new bucket starts completely full at that
                   amount — so the first requests against a fresh key can
                   burst up to (capacity + burst) before being throttled.

        Returns:
            RateLimitResult with allowed, remaining, reset_at, retry_after.
            `remaining` is clamped to `limit`, so it never exceeds the
            advertised quota even if the bucket is currently holding extra
            burst tokens.

        Raises:
            ValueError: if `limit` or `window` is not a positive number.
        """
        # Guard against configs that would otherwise cause division by
        # zero in the refill-rate / retry_after math below.
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        if window <= 0:
            raise ValueError("window must be a positive integer")

        now = time.time()
        capacity = float(limit)
        refill_rate = capacity / float(window)  # tokens per second

        # Only use default burst if not explicitly set (None)
        if burst is None:
            burst = int(capacity)
        else:
            burst = int(burst)

        # Execute the token bucket Lua script atomically
        result = await self.backend.execute_lua(
            script="""
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local requested = tonumber(ARGV[4])
            local burst_allowance = tonumber(ARGV[5])

            -- Get current state or initialize
            local state = redis.call('GET', key)
            local tokens, last_refill
            local max_tokens = capacity + burst_allowance

            if state == false then
              -- Initialize with a full bucket (capacity + burst)
              tokens = max_tokens
              last_refill = now
            else
              local parts = {}
              for part in string.gmatch(state, '[^:]+') do
                table.insert(parts, part)
              end
              tokens = tonumber(parts[1])
              last_refill = tonumber(parts[2])
            end

            -- Refill based on elapsed time
            local elapsed = now - last_refill
            tokens = tokens + (elapsed * refill_rate)

            -- Cap at capacity + burst
            if tokens > max_tokens then
              tokens = max_tokens
            end

            -- Check if we can allow this request
            local allowed = 0
            if tokens >= requested then
              allowed = 1
              tokens = tokens - requested
            end

            -- Save state (always update last_refill to prevent token creep)
            local ttl = math.ceil((max_tokens / refill_rate) + 10)
            redis.call('SET', key, tokens .. ':' .. now, 'EX', ttl)

            -- Return [allowed, floor(tokens), exact tokens as string].
            -- The exact value lets Python compute a precise retry_after
            -- even when tokens is a small fraction (e.g. 0.95).
            return {allowed, math.floor(tokens), tostring(tokens)}
            """,
            keys=[key],
            args=[str(capacity), str(refill_rate), str(now), "1.0", str(burst)],
        )

        allowed = bool(result[0])
        tokens_remaining = float(
            result[2]
        )  # exact value, may include fractional/burst tokens

        # Cap the reported `remaining` at `limit` so callers never see
        # remaining > limit, even though the bucket itself can briefly
        # hold up to capacity + burst tokens.
        remaining = min(int(result[1]), limit)

        # reset_at: when the bucket will hold `limit` tokens again (i.e.
        # the caller's full quota is back), assuming no further requests.
        if tokens_remaining >= limit:
            # Already at or above full quota — nothing to wait for.
            reset_at = int(now)
        else:
            tokens_needed = limit - tokens_remaining
            time_to_full = tokens_needed / refill_rate
            reset_at = int(now + time_to_full)

        retry_after = None
        if not allowed:
            # tokens_remaining is < 1 here (otherwise the request would
            # have been allowed). Compute exactly how long until one more
            # token accumulates, rounding up so we never tell the caller
            # to retry before a token is actually available.
            tokens_needed = 1.0 - tokens_remaining
            retry_after = max(1, math.ceil(tokens_needed / refill_rate))

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )
