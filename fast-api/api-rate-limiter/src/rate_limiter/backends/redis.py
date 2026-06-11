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

    async def close(self) -> None:
        await self._client.aclose()
        await self._pool.aclose()
