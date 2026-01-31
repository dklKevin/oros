"""
Pytest configuration and fixtures for retrieval service tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from services.shared.config import Settings
from services.shared.database import get_db


# In-memory storage for test data
_test_documents: dict[str, Any] = {}
_test_chunks: dict[str, Any] = {}


def reset_test_data():
    """Reset test data storage."""
    global _test_documents, _test_chunks
    _test_documents = {}
    _test_chunks = {}


class FakeAsyncSession:
    """Fake async database session for testing."""

    def __init__(self):
        self._added = []
        self._committed = False

    def add(self, obj):
        """Track added objects."""
        self._added.append(obj)

    async def flush(self):
        """Flush changes."""
        pass

    async def commit(self):
        """Commit changes."""
        self._committed = True

    async def rollback(self):
        """Rollback changes."""
        pass

    async def close(self):
        """Close session."""
        pass

    async def execute(self, query, params=None):
        """Execute a query and return mock result."""
        result = MagicMock()
        query_str = str(query)

        # Return empty results for most queries in tests
        if 'documents' in query_str.lower():
            result.scalar_one_or_none = MagicMock(return_value=None)
            result.scalar = MagicMock(return_value=0)
        elif 'chunks' in query_str.lower():
            result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            result.scalar = MagicMock(return_value=0)
        else:
            result.scalar_one_or_none = MagicMock(return_value=None)
            result.scalar = MagicMock(return_value=0)

        # For raw SQL queries (like hybrid_search), provide fetchall
        result.fetchall = MagicMock(return_value=[])
        result.all = MagicMock(return_value=[])

        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def override_get_db() -> AsyncGenerator[FakeAsyncSession, None]:
    """Override database dependency for tests."""
    session = FakeAsyncSession()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="development",
        database_url="postgresql://test:test@localhost:5432/test",
        log_level="DEBUG",
        log_format="text",
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client for sync tests with mocked database."""
    from services.retrieval.src.main import app

    # Reset test data for each test
    reset_test_data()

    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db

    # Mock the lifespan context to skip actual DB initialization
    async def mock_init_db():
        pass

    async def mock_close_db():
        pass

    with patch("services.retrieval.src.main.init_db", mock_init_db):
        with patch("services.retrieval.src.main.close_db", mock_close_db):
            with patch(
                "services.retrieval.src.main.db_health_check",
                AsyncMock(return_value={"status": "healthy", "pool_size": 5}),
            ):
                with TestClient(app) as c:
                    yield c

    # Clear dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    from services.retrieval.src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_search_request() -> dict[str, Any]:
    """Sample search request for testing."""
    return {
        "query": "CRISPR gene editing mechanisms",
        "search_type": "hybrid",
        "limit": 10,
        "offset": 0,
        "filters": {
            "date_from": "2020-01-01",
            "date_to": "2024-12-31",
        },
    }


@pytest.fixture
def sample_chat_request() -> dict[str, Any]:
    """Sample chat request for testing."""
    return {
        "query": "What are the main applications of CRISPR in treating cardiovascular diseases?",
        "max_chunks": 5,
        "conversation_history": [],
    }


@pytest.fixture
def sample_chunk_data() -> dict[str, Any]:
    """Sample chunk data for testing."""
    return {
        "id": str(uuid4()),
        "document_id": str(uuid4()),
        "content": "CRISPR-Cas9 is a revolutionary gene editing technology...",
        "section_title": "Introduction",
        "chunk_index": 0,
        "token_count": 150,
        "embedding": [0.1] * 1536,  # Placeholder embedding
    }
