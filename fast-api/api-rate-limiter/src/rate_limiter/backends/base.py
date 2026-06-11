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
