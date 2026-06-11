import pytest
import src.rate_limiter.main as app_module
from httpx import ASGITransport, AsyncClient
from src.rate_limiter.algorithms.fixed_window import FixedWindowAlgorithm
from src.rate_limiter.backends.memory import InMemoryBackend
from src.rate_limiter.main import app


@pytest.fixture
def memory_backend():
    return InMemoryBackend()


@pytest.fixture
def fixed_window(memory_backend):
    return FixedWindowAlgorithm(memory_backend)


@pytest.fixture
async def client(memory_backend):
    """
    AsyncClient with the real FastAPI app wired to an in-memory backend.
    No Redis needed for unit tests.
    """
    app_module.backend = memory_backend
    app_module.fixed_window = FixedWindowAlgorithm(memory_backend)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
