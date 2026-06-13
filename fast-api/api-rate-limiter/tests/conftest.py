import pytest
from httpx import ASGITransport, AsyncClient

from rate_limiter.algorithms.fixed_window import FixedWindowAlgorithm
from rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from rate_limiter.algorithms.sliding_window import SlidingWindowAlgorithm
from rate_limiter.algorithms.token_bucket import TokenBucketAlgorithm
from rate_limiter.backends.memory import InMemoryBackend
from rate_limiter.main import app


@pytest.fixture
def memory_backend():
    return InMemoryBackend()


@pytest.fixture
def fixed_window(memory_backend):
    return FixedWindowAlgorithm(memory_backend)


@pytest.fixture
async def client(memory_backend):
    """AsyncClient with the real FastAPI app wired to an in-memory backend."""
    app.state.backend = memory_backend
    app.state.fixed_window = FixedWindowAlgorithm(memory_backend)
    app.state.sliding_window = SlidingWindowAlgorithm(memory_backend)
    app.state.token_bucket = TokenBucketAlgorithm(memory_backend)
    app.state.leaky_bucket = LeakyBucketAlgorithm(memory_backend)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
