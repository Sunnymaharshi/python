import redis.asyncio as aioredis

from .base import BaseBackend


class RedisBackend(BaseBackend):
    """
    Production Redis backend using redis-py async client with hiredis parser.
    All operations map 1:1 to Redis commands — no extra abstraction overhead.
    """

    def __init__(self, redis_url: str, max_connections: int = 20) -> None:
        self._pool = aioredis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            decode_responses=True,  # always return str, not bytes
        )
        self._client = aioredis.Redis(connection_pool=self._pool)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str | int, ex: int | None = None) -> None:
        await self._client.set(key, value, ex=ex)

    async def incr(self, key: str) -> int:
        return await self._client.incr(key)

    async def expire(self, key: str, seconds: int) -> None:
        await self._client.expire(key, seconds)

    async def execute_lua(self, script: str, keys: list[str], args: list) -> object:
        """
        Execute a Lua script atomically via Redis EVAL.
        Redis guarantees the entire script runs without interruption —
        this is how we avoid race conditions in token bucket / leaky bucket.
        """
        lua = self._client.register_script(script)
        return await lua(keys=keys, args=args)

    # ── Sorted set operations (used by sliding window) ────────────────────────
    # These map directly to Redis sorted set commands.
    # Sorted sets store members ordered by score — perfect for timestamps.

    async def zadd(self, key: str, score: float, member: str) -> int:
        """
        Add a member with a score to the sorted set.
        In sliding window: score = timestamp, member = str(timestamp)
        Returns number of elements added.
        """
        return await self._client.zadd(key, {member: score})

    async def zcard(self, key: str) -> int:
        """
        Return the number of members in the sorted set.
        In sliding window: this is the request count within the current window.
        O(1) operation.
        """
        return await self._client.zcard(key)

    async def zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> int:
        """
        Remove all members with scores between min_score and max_score (inclusive).
        In sliding window: removes all timestamps older than (now - window).
        This keeps the sorted set from growing unboundedly.
        Returns number of elements removed.
        """
        return await self._client.zremrangebyscore(key, min_score, max_score)

    async def close(self) -> None:
        await self._client.aclose()
        await self._pool.aclose()
