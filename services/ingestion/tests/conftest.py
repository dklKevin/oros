"""
Pytest configuration and fixtures for ingestion service tests.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from services.shared.config import Settings


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


# In-memory storage for test data
_test_documents: dict[str, Any] = {}
_test_jobs: dict[str, Any] = {}


def reset_test_data():
    """Reset test data storage."""
    global _test_documents, _test_jobs
    _test_documents = {}
    _test_jobs = {}


class FakeAsyncSession:
    """Fake async database session for testing."""

    def __init__(self):
        self._added = []
        self._committed = False

    def add(self, obj):
        """Track added objects and store in test storage."""
        self._added.append(obj)
        # Store in appropriate test storage based on type
        if hasattr(obj, '__tablename__'):
            if obj.__tablename__ == 'documents':
                _test_documents[str(obj.id)] = obj
            elif obj.__tablename__ == 'processing_jobs':
                _test_jobs[str(obj.id)] = obj

    async def flush(self):
        """Flush changes - commit to test storage."""
        # Objects are already in test storage from add()
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

    async def execute(self, query):
        """Execute a query and return mock result."""
        result = MagicMock()

        # Try to extract what we're looking for from the query
        query_str = str(query)

        # Check if this is a job lookup
        if 'processing_jobs' in query_str.lower():
            # For SQLAlchemy select, extract param value from whereclause
            if hasattr(query, '_where_criteria') and query._where_criteria:
                for criterion in query._where_criteria:
                    if hasattr(criterion, 'right') and hasattr(criterion.right, 'value'):
                        param_value = str(criterion.right.value)
                        if param_value in _test_jobs:
                            result.scalar_one_or_none = MagicMock(return_value=_test_jobs[param_value])
                            return result

            result.scalar_one_or_none = MagicMock(return_value=None)
        elif 'documents' in query_str.lower():
            result.scalar_one_or_none = MagicMock(return_value=None)
            result.scalar = MagicMock(return_value=0)
        else:
            result.scalar_one_or_none = MagicMock(return_value=None)
            result.scalar = MagicMock(return_value=0)

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


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client for sync tests with mocked database."""
    from services.shared.database import get_db
    from services.ingestion.src.main import app

    # Reset test data for each test
    reset_test_data()

    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db

    # Mock the lifespan context to skip actual DB initialization
    async def mock_init_db():
        pass

    async def mock_close_db():
        pass

    with patch("services.ingestion.src.main.init_db", mock_init_db):
        with patch("services.ingestion.src.main.close_db", mock_close_db):
            with patch(
                "services.ingestion.src.main.db_health_check",
                AsyncMock(return_value={"status": "healthy", "pool_size": 5}),
            ):
                with TestClient(app) as c:
                    yield c

    # Clear dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    from services.ingestion.src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_pubmed_xml() -> str:
    """Sample PubMed XML for testing."""
    return """<?xml version="1.0"?>
    <pmc-articleset>
        <article>
            <front>
                <article-meta>
                    <article-id pub-id-type="pmcid">PMC123456</article-id>
                    <article-id pub-id-type="doi">10.1234/test.2024</article-id>
                    <title-group>
                        <article-title>Test Article Title</article-title>
                    </title-group>
                    <contrib-group>
                        <contrib contrib-type="author">
                            <name><surname>Smith</surname><given-names>John</given-names></name>
                        </contrib>
                    </contrib-group>
                    <pub-date pub-type="epub">
                        <day>15</day><month>1</month><year>2024</year>
                    </pub-date>
                    <abstract>
                        <p>This is a test abstract for the article.</p>
                    </abstract>
                </article-meta>
            </front>
            <body>
                <sec>
                    <title>Introduction</title>
                    <p>This is the introduction section.</p>
                </sec>
                <sec>
                    <title>Methods</title>
                    <p>This is the methods section.</p>
                </sec>
            </body>
        </article>
    </pmc-articleset>
    """


@pytest.fixture
def sample_document_data() -> dict[str, Any]:
    """Sample document data for testing."""
    return {
        "title": "Test Article Title",
        "abstract": "This is a test abstract.",
        "authors": [{"given_names": "John", "surname": "Smith"}],
        "journal": "Test Journal",
        "publication_date": "2024-01-15",
        "doi": "10.1234/test.2024",
        "pmcid": "PMC123456",
    }


@pytest.fixture
def sample_xml_path() -> str:
    """Path to a sample XML file in test-data."""
    import os

    return os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        ),
        "test-data",
        "papers",
        "PMC9408902.xml",
    )


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    return mock_session


@pytest.fixture
def mock_processor():
    """Mock DocumentProcessor."""
    from services.ingestion.src.processor import ProcessingResult

    mock = AsyncMock()
    mock.process_document = AsyncMock(
        return_value=ProcessingResult(
            document_id=uuid4(),
            success=True,
            chunks_created=10,
        )
    )
    mock.process_local_file = AsyncMock(
        return_value=ProcessingResult(
            document_id=uuid4(),
            success=True,
            chunks_created=15,
        )
    )

    return mock
