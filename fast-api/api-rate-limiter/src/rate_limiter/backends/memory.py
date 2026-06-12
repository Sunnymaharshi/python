import asyncio
import time

from .base import BaseBackend


class InMemoryBackend(BaseBackend):
    """
    Single-process in-memory backend — for unit tests and local dev only.
    NOT safe for multi-process or distributed deployments.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}
        # Sorted sets stored separately: key -> list of (score, member)
        self._zsets: dict[str, list[tuple[float, str]]] = {}
        self._lock = asyncio.Lock()

    def _is_expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, expire_at = self._store[key]
        if expire_at is not None and time.time() > expire_at:
            del self._store[key]
            return True
        return False

    # ── Key/value ops ─────────────────────────────────────────────────────────

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

    # ── Sorted set ops (used by sliding window) ───────────────────────────────

    async def zadd(self, key: str, score: float, member: str) -> None:
        async with self._lock:
            if key not in self._zsets:
                self._zsets[key] = []
            # Remove existing entry for this member if present (upsert behaviour)
            self._zsets[key] = [(s, m) for s, m in self._zsets[key] if m != member]
            self._zsets[key].append((score, member))

    async def zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> None:
        async with self._lock:
            if key not in self._zsets:
                return
            self._zsets[key] = [
                (s, m) for s, m in self._zsets[key] if not (min_score <= s <= max_score)
            ]

    async def zcard(self, key: str) -> int:
        async with self._lock:
            return len(self._zsets.get(key, []))

    async def zrange_by_score(
        self, key: str, min_score: float, max_score: float
    ) -> list[str]:
        async with self._lock:
            if key not in self._zsets:
                return []
            return [m for s, m in self._zsets[key] if min_score <= s <= max_score]

    # ── Lua emulation (token bucket only) ────────────────────────────────────

    async def execute_lua(self, script: str, keys: list[str], args: list) -> object:
        async with self._lock:
            key = keys[0]
            capacity = float(args[0])
            refill_rate = float(args[1])
            now = float(args[2])
            requested = float(args[3])
            burst_allowance = float(args[4]) if len(args) > 4 else 0
            max_tokens = capacity + burst_allowance

            if self._is_expired(key):
                tokens = max_tokens  # Initialize with full bucket
                last_refill = now
            else:
                raw, _ = self._store.get(key, ("", None))
                if raw:
                    parts = raw.split(":")
                    tokens = float(parts[0])
                    last_refill = float(parts[1])
                else:
                    tokens = max_tokens
                    last_refill = now

            elapsed = now - last_refill
            tokens = tokens + elapsed * refill_rate

            # Cap at capacity + burst
            tokens = min(max_tokens, tokens)

            if tokens >= requested:
                tokens -= requested
                allowed = 1
            else:
                allowed = 0

            expire_at = time.time() + int(capacity / refill_rate) + 10
            self._store[key] = (f"{tokens}:{now}", expire_at)
            return [allowed, int(tokens)]

    async def close(self) -> None:
        self._store.clear()
        self._zsets.clear()
