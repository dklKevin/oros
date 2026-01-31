"""
E2E Tests for Ingestion Service.

Tests the complete ingestion flow against a real PostgreSQL database.
"""

import pytest
from uuid import UUID


@pytest.mark.e2e
class TestIngestionHealthE2E:
    """E2E tests for ingestion service health."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, ingestion_client):
        """Health endpoint should return healthy when connected to real DB."""
        response = await ingestion_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ingestion"
        assert "database" in data


@pytest.mark.e2e
class TestIngestionCreateDocumentE2E:
    """E2E tests for document creation."""

    @pytest.mark.asyncio
    async def test_ingest_creates_document_and_job(self, ingestion_client, e2e_db):
        """POST /ingest should create document and processing job in database."""
        response = await ingestion_client.post(
            "/ingest",
            json={"s3_key": "documents/e2e-test-doc.xml"},
        )

        assert response.status_code == 202
        data = response.json()

        # Verify response structure
        assert "document_id" in data
        assert "job_id" in data
        # Status can be "queued" or "pending" depending on processing state
        assert data["status"] in ("queued", "pending")

        # Verify document was created in database
        from sqlalchemy import select
        from services.shared.models import Document

        doc_id = UUID(data["document_id"])
        result = await e2e_db.execute(
            select(Document).where(Document.id == doc_id)
        )
        document = result.scalar_one_or_none()

        assert document is not None
        assert document.s3_key == "documents/e2e-test-doc.xml"
        # processing_status can be enum or string depending on how it's loaded
        status = document.processing_status
        if hasattr(status, "value"):
            status = status.value
        assert status == "pending"

    @pytest.mark.asyncio
    async def test_ingest_with_source_url(self, ingestion_client, e2e_db):
        """POST /ingest with source_url should create document."""
        response = await ingestion_client.post(
            "/ingest",
            json={
                "source_url": "https://example.com/paper.xml",
                "s3_key": "documents/from-url.xml",
            },
        )

        assert response.status_code == 202
        data = response.json()

        # Verify document has source_url
        from sqlalchemy import select
        from services.shared.models import Document

        doc_id = UUID(data["document_id"])
        result = await e2e_db.execute(
            select(Document).where(Document.id == doc_id)
        )
        document = result.scalar_one_or_none()

        assert document is not None
        assert document.source_url == "https://example.com/paper.xml"

    @pytest.mark.asyncio
    async def test_ingest_rejects_empty_request(self, ingestion_client):
        """POST /ingest without s3_key or source_url should return 400."""
        response = await ingestion_client.post("/ingest", json={})

        assert response.status_code in (400, 422)  # 422 for Pydantic validation
        # Check for common error indicators
        detail = response.json().get("detail", "")
        if isinstance(detail, str):
            assert "source_url" in detail.lower() or "s3_key" in detail.lower()


@pytest.mark.e2e
class TestIngestionStatusE2E:
    """E2E tests for job status endpoint."""

    @pytest.mark.asyncio
    async def test_status_returns_job_info(self, ingestion_client, e2e_db):
        """GET /status/{job_id} should return job information."""
        # First create a document
        create_response = await ingestion_client.post(
            "/ingest",
            json={"s3_key": "documents/status-test.xml"},
        )
        job_id = create_response.json()["job_id"]

        # Check status
        status_response = await ingestion_client.get(f"/status/{job_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert "document_id" in data

    @pytest.mark.asyncio
    async def test_status_returns_404_for_unknown_job(self, ingestion_client):
        """GET /status/{job_id} should return 404 for unknown job."""
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = await ingestion_client.get(f"/status/{fake_job_id}")

        assert response.status_code == 404


@pytest.mark.e2e
class TestIngestionMetricsE2E:
    """E2E tests for metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_returns_counts(self, ingestion_client, e2e_db):
        """GET /metrics should return document and job counts."""
        # Create some documents first
        await ingestion_client.post(
            "/ingest",
            json={"s3_key": "documents/metrics-test-1.xml"},
        )
        await ingestion_client.post(
            "/ingest",
            json={"s3_key": "documents/metrics-test-2.xml"},
        )

        # Get metrics
        response = await ingestion_client.get("/metrics")

        assert response.status_code == 200
        data = response.json()

        # Verify metrics structure (actual field names from API)
        assert "documents_pending_total" in data
        # Should have at least 2 pending documents
        assert data["documents_pending_total"] >= 2
