from abc import ABC, abstractmethod


class BaseBackend(ABC):
    """
    Abstract storage backend for rate limiter state.
    Implement this to add new backends (PostgreSQL, Memcached, etc.)
    """

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Return the value for key, or None if not set."""

    @abstractmethod
    async def set(self, key: str, value: str | int, ex: int | None = None) -> None:
        """Set key to value, with optional TTL in seconds."""

    @abstractmethod
    async def incr(self, key: str) -> int:
        """Atomically increment key by 1. Creates key at 0 if missing."""

    @abstractmethod
    async def expire(self, key: str, seconds: int) -> None:
        """Set TTL on an existing key."""

    @abstractmethod
    async def execute_lua(self, script: str, keys: list[str], args: list) -> object:
        """Run a Lua script atomically. Used by token bucket & leaky bucket."""

    @abstractmethod
    async def close(self) -> None:
        """Clean up connections."""

    # ── Sorted set operations (used by Sliding Window) ────────────────────────

    @abstractmethod
    async def zadd(self, key: str, score: float, member: str) -> None:
        """Add member with score to a sorted set."""

    @abstractmethod
    async def zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> None:
        """Remove all members with scores between min and max (inclusive)."""

    @abstractmethod
    async def zcard(self, key: str) -> int:
        """Return the number of members in the sorted set."""

    @abstractmethod
    async def zrange_by_score(
        self, key: str, min_score: float, max_score: float
    ) -> list[str]:
        """Return all members with scores between min and max."""

    @abstractmethod
    async def zrange_with_scores(
        self, key: str, start: int, stop: int
    ) -> list[tuple[str, float]]:
        """
        Return a range of (member, score) pairs ordered by score ascending.
        zrange_with_scores(key, 0, 0) returns the single OLDEST entry —
        used by sliding window to compute accurate reset_at / retry_after.
        """
