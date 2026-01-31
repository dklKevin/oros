"""
E2E Test Configuration and Fixtures.

These tests run against real PostgreSQL database in Docker.
Requires: docker-compose -f docker-compose.e2e.yml up -d
"""

import os
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# E2E Database URL - connects to Docker PostgreSQL
E2E_DATABASE_URL = os.environ.get(
    "E2E_DATABASE_URL",
    "postgresql+asyncpg://biomedical:test_password@localhost:5433/knowledge_platform_e2e"
)

# E2E S3 endpoint
E2E_S3_ENDPOINT = os.environ.get(
    "E2E_S3_ENDPOINT",
    "http://localhost:4567"
)


@pytest_asyncio.fixture
async def e2e_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test.

    Creates a fresh engine and session for each test to avoid event loop issues.
    Cleans up test data after each test.
    """
    # Create engine fresh for each test to avoid event loop conflicts
    engine = create_async_engine(
        E2E_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        try:
            yield session
        finally:
            # Rollback any pending transaction
            await session.rollback()
            # Cleanup - truncate tables after each test
            try:
                await session.execute(text("TRUNCATE chunks CASCADE"))
                await session.execute(text("TRUNCATE documents CASCADE"))
                await session.execute(text("TRUNCATE processing_jobs CASCADE"))
                await session.execute(text("TRUNCATE search_history CASCADE"))
                await session.commit()
            except Exception:
                # If cleanup fails, just rollback
                await session.rollback()

    # Dispose of the engine after the test
    await engine.dispose()


# Test-only AWS credentials (loaded from environment with fallback for CI)
# These should NEVER be real credentials
E2E_AWS_ACCESS_KEY_ID = os.environ.get("E2E_AWS_ACCESS_KEY_ID", "testing")
E2E_AWS_SECRET_ACCESS_KEY = os.environ.get("E2E_AWS_SECRET_ACCESS_KEY", "testing")
E2E_AWS_REGION = os.environ.get("E2E_AWS_REGION", "us-east-1")


@pytest.fixture
def e2e_settings():
    """
    E2E test settings.

    Note: Uses test-only credentials that are safe for CI environments.
    Real AWS credentials should NEVER be used in tests.
    """
    from services.shared.config import Settings

    return Settings(
        environment="development",
        database_url=E2E_DATABASE_URL.replace("+asyncpg", ""),
        aws_endpoint_url=E2E_S3_ENDPOINT,
        aws_access_key_id=E2E_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=E2E_AWS_SECRET_ACCESS_KEY,
        aws_region=E2E_AWS_REGION,
        log_level="DEBUG",
        log_format="text",
    )


@pytest_asyncio.fixture
async def ingestion_client(e2e_db, e2e_settings) -> AsyncGenerator[AsyncClient, None]:
    """
    Create async client for ingestion service E2E tests.

    Connects to real database via dependency override.
    """
    from unittest.mock import patch, AsyncMock
    from services.ingestion.src.main import app
    from services.shared.database import get_db

    # Override database dependency
    async def override_get_db():
        yield e2e_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock lifespan database operations
    with patch("services.ingestion.src.main.init_db", AsyncMock()):
        with patch("services.ingestion.src.main.close_db", AsyncMock()):
            with patch(
                "services.ingestion.src.main.db_health_check",
                AsyncMock(return_value={"status": "healthy", "pool_size": 5}),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                    timeout=30.0,
                ) as client:
                    yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def retrieval_client(e2e_db, e2e_settings) -> AsyncGenerator[AsyncClient, None]:
    """
    Create async client for retrieval service E2E tests.

    Connects to real database via dependency override.
    """
    from unittest.mock import patch, AsyncMock
    from services.retrieval.src.main import app
    from services.shared.database import get_db

    # Override database dependency
    async def override_get_db():
        yield e2e_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock lifespan database operations
    with patch("services.retrieval.src.main.init_db", AsyncMock()):
        with patch("services.retrieval.src.main.close_db", AsyncMock()):
            with patch(
                "services.retrieval.src.main.db_health_check",
                AsyncMock(return_value={"status": "healthy", "pool_size": 5}),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                    timeout=30.0,
                ) as client:
                    yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_document(e2e_db) -> dict[str, Any]:
    """
    Create a sample document directly in the database.

    Returns document data for use in tests.
    """
    from services.shared.models import Document, ProcessingStatus

    doc = Document(
        id=uuid4(),
        title="CRISPR-Cas9 Gene Editing in Cardiovascular Disease",
        abstract="This study investigates the application of CRISPR-Cas9 technology...",
        authors=[
            {"given_names": "John", "surname": "Smith"},
            {"given_names": "Jane", "surname": "Doe"},
        ],
        journal="Nature Biotechnology",
        publication_date=date(2024, 1, 15),
        doi="10.1038/test.2024.001",
        pmcid="PMC12345678",
        s3_key="documents/test-doc.xml",
        processing_status=ProcessingStatus.COMPLETED,
        has_abstract=True,
        has_full_text=True,
        section_count=5,
        word_count=5000,
        quality_score=0.85,
    )

    e2e_db.add(doc)
    await e2e_db.flush()

    return {
        "id": doc.id,
        "title": doc.title,
        "abstract": doc.abstract,
        "doi": doc.doi,
        "pmcid": doc.pmcid,
    }


@pytest_asyncio.fixture
async def sample_chunks(e2e_db, sample_document) -> list[dict[str, Any]]:
    """
    Create sample chunks for a document.

    Returns list of chunk data for use in tests.
    """
    from services.shared.models import Chunk

    chunks_data = [
        {
            "content": "CRISPR-Cas9 is a revolutionary gene editing technology that allows precise modifications to DNA sequences.",
            "section_title": "Introduction",
            "section_type": "introduction",
        },
        {
            "content": "The cardiovascular applications of CRISPR include treating inherited heart diseases and atherosclerosis.",
            "section_title": "Applications",
            "section_type": "results",
        },
        {
            "content": "Gene therapy using CRISPR shows promise for familial hypercholesterolemia treatment.",
            "section_title": "Discussion",
            "section_type": "discussion",
        },
    ]

    created_chunks = []
    for i, chunk_data in enumerate(chunks_data):
        chunk = Chunk(
            id=uuid4(),
            document_id=sample_document["id"],
            content=chunk_data["content"],
            section_title=chunk_data["section_title"],
            section_type=chunk_data["section_type"],
            chunk_index=i,
            token_count=len(chunk_data["content"].split()),
            # Note: embeddings would be added by real embedding service
            embedding=None,
        )
        e2e_db.add(chunk)
        created_chunks.append({
            "id": chunk.id,
            "content": chunk.content,
            "section_title": chunk.section_title,
        })

    await e2e_db.flush()
    return created_chunks


@pytest.fixture
def sample_pubmed_xml() -> bytes:
    """Sample PubMed XML content for ingestion tests."""
    return b"""<?xml version="1.0"?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.2 20190208//EN" "https://jats.nlm.nih.gov/publishing/1.2/JATS-journalpublishing1.dtd">
<article>
    <front>
        <journal-meta>
            <journal-title-group>
                <journal-title>Test Journal of Biomedical Engineering</journal-title>
            </journal-title-group>
        </journal-meta>
        <article-meta>
            <article-id pub-id-type="pmcid">PMC99999999</article-id>
            <article-id pub-id-type="doi">10.1234/e2e.test.2024</article-id>
            <title-group>
                <article-title>E2E Test: Novel Gene Therapy Approaches</article-title>
            </title-group>
            <contrib-group>
                <contrib contrib-type="author">
                    <name>
                        <surname>TestAuthor</surname>
                        <given-names>E2E</given-names>
                    </name>
                </contrib>
            </contrib-group>
            <pub-date pub-type="epub">
                <day>01</day>
                <month>01</month>
                <year>2024</year>
            </pub-date>
            <abstract>
                <p>This is an E2E test abstract about gene therapy and CRISPR applications.</p>
            </abstract>
        </article-meta>
    </front>
    <body>
        <sec>
            <title>Introduction</title>
            <p>Gene therapy represents a revolutionary approach to treating genetic disorders.</p>
            <p>CRISPR-Cas9 technology has enabled precise genome editing capabilities.</p>
        </sec>
        <sec>
            <title>Methods</title>
            <p>We employed CRISPR-Cas9 with guide RNAs targeting specific genetic loci.</p>
        </sec>
        <sec>
            <title>Results</title>
            <p>Our results demonstrate successful gene editing in cardiovascular tissue samples.</p>
        </sec>
        <sec>
            <title>Discussion</title>
            <p>These findings suggest promising therapeutic applications for heart disease.</p>
        </sec>
    </body>
</article>
"""
