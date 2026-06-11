from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..backends.base import BaseBackend


@dataclass
class RateLimitResult:
    """
    Returned by every algorithm's check() call.
    Contains everything needed to build correct HTTP rate limit headers.
    """

    allowed: bool  # True → request passes, False → 429
    limit: int  # X-RateLimit-Limit: total requests allowed per window
    remaining: int  # X-RateLimit-Remaining: requests left in current window
    reset_at: int  # X-RateLimit-Reset: Unix timestamp when window resets
    retry_after: int | None = None  # Retry-After seconds — only set when blocked


class BaseAlgorithm(ABC):
    """
    All rate limiting algorithms implement this interface.
    One method: check(). Returns a RateLimitResult — caller decides what to do with it.
    """

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    @abstractmethod
    async def check(
        self,
        key: str,  # e.g. "rl:fixed:user:42:/api/data"
        limit: int,  # max requests allowed
        window: int,  # window size in seconds
    ) -> RateLimitResult:
        """
        Check whether this request should be allowed.
        Must be safe to call concurrently from many async tasks.
        """
