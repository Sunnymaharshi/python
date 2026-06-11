import asyncio
import time
from .base import BaseBackend


class InMemoryBackend(BaseBackend):
    """
    Single-process in-memory backend — for unit tests and local dev only.
    NOT safe for multi-process or distributed deployments.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = (
            {}
        )  # key -> (value, expire_at)
        self._lock = asyncio.Lock()

    def _is_expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, expire_at = self._store[key]
        if expire_at is not None and time.time() > expire_at:
            del self._store[key]
            return True
        return False

    async def get(self, key: str) -> str | None:
        async with self._lock:
            if self._is_expired(key):
                return None
            value, _ = self._store[key]
            return value

    async def set(self, key: str, value: str | int, ex: int | None = None) -> None:
        async with self._lock:
            expire_at = time.time() + ex if ex else None
            self._store[key] = (str(value), expire_at)

    async def incr(self, key: str) -> int:
        async with self._lock:
            if self._is_expired(key):
                self._store[key] = ("1", None)
                return 1
            value, expire_at = self._store[key]
            new_val = int(value) + 1
            self._store[key] = (str(new_val), expire_at)
            return new_val

    async def expire(self, key: str, seconds: int) -> None:
        async with self._lock:
            if key in self._store:
                value, _ = self._store[key]
                self._store[key] = (value, time.time() + seconds)

    async def execute_lua(self, script: str, keys: list[str], args: list) -> object:
        """
        Naive Lua emulation for tests — only supports the token bucket script.
        Real atomicity guarantees only come from the Redis backend.
        """
        async with self._lock:
            key = keys[0]
            capacity = float(args[0])
            refill_rate = float(args[1])  # tokens per second
            now = float(args[2])
            requested = float(args[3])

            if self._is_expired(key):
                tokens = capacity
                last_refill = now
            else:
                raw, _ = self._store.get(key, ("", None))
                parts = raw.split(":")
                tokens = float(parts[0])
                last_refill = float(parts[1])

            # Refill based on elapsed time
            elapsed = now - last_refill
            tokens = min(capacity, tokens + elapsed * refill_rate)

            if tokens >= requested:
                tokens -= requested
                allowed = 1
            else:
                allowed = 0

            expire_at = time.time() + int(capacity / refill_rate) + 1
            self._store[key] = (f"{tokens}:{now}", expire_at)
            return [allowed, int(tokens)]

    async def close(self) -> None:
        self._store.clear()
