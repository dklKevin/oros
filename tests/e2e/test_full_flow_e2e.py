"""
E2E Tests for Full Flow.

Tests the complete pipeline: Ingest → Process → Search → Chat
"""

import pytest
from uuid import UUID


@pytest.mark.e2e
class TestFullIngestionToSearchFlowE2E:
    """E2E tests for the complete ingest-to-search flow."""

    @pytest.mark.asyncio
    async def test_ingest_then_search_finds_document(
        self, ingestion_client, retrieval_client, e2e_db
    ):
        """
        Full flow test: Ingest a document, then search should find it.

        Note: This test simulates the manual completion of processing
        since background tasks don't run in test mode.
        """
        # Step 1: Ingest a document
        ingest_response = await ingestion_client.post(
            "/ingest",
            json={"s3_key": "documents/full-flow-test.xml"},
        )
        assert ingest_response.status_code == 202
        doc_id = UUID(ingest_response.json()["document_id"])

        # Step 2: Manually update document to "completed" status
        # (In real scenario, background worker would process it)
        from sqlalchemy import update
        from services.shared.models import Document, ProcessingStatus

        await e2e_db.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(
                title="Full Flow Test: CRISPR Applications",
                abstract="Testing the complete flow from ingestion to search.",
                processing_status=ProcessingStatus.COMPLETED,
                has_abstract=True,
                has_full_text=True,
            )
        )
        await e2e_db.commit()

        # Step 3: Add a chunk with searchable content
        from services.shared.models import Chunk

        chunk = Chunk(
            document_id=doc_id,
            content="This is a test chunk about CRISPR gene editing technology for cardiovascular disease treatment.",
            section_title="Test Section",
            section_type="body",
            chunk_index=0,
            token_count=15,
        )
        e2e_db.add(chunk)
        await e2e_db.commit()

        # Step 4: Search should now find the document (use keyword search - no embeddings in test)
        search_response = await retrieval_client.post(
            "/search",
            json={
                "query": "CRISPR cardiovascular",
                "search_type": "keyword",  # Must use keyword - no embeddings
                "limit": 10,
            },
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Should find our document
        assert data["total"] >= 1
        assert len(data["results"]) >= 1

        # Verify the result is our document
        found_doc_ids = [r["document_id"] for r in data["results"]]
        assert str(doc_id) in found_doc_ids

    @pytest.mark.asyncio
    async def test_document_status_transitions(self, ingestion_client, e2e_db):
        """Test document processing status transitions."""
        # Step 1: Ingest - should be pending
        ingest_response = await ingestion_client.post(
            "/ingest",
            json={"s3_key": "documents/status-transition-test.xml"},
        )
        doc_id = UUID(ingest_response.json()["document_id"])
        job_id = ingest_response.json()["job_id"]

        # Verify initial status
        status_response = await ingestion_client.get(f"/status/{job_id}")
        assert status_response.json()["status"] == "pending"

        # Step 2: Simulate processing start
        from sqlalchemy import update
        from services.shared.models import ProcessingJob, ProcessingStatus

        await e2e_db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == UUID(job_id))
            .values(status=ProcessingStatus.PROCESSING)
        )
        await e2e_db.commit()

        # Verify processing status
        status_response = await ingestion_client.get(f"/status/{job_id}")
        assert status_response.json()["status"] == "processing"

        # Step 3: Simulate completion
        await e2e_db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == UUID(job_id))
            .values(status=ProcessingStatus.COMPLETED)
        )
        await e2e_db.commit()

        # Verify completed status
        status_response = await ingestion_client.get(f"/status/{job_id}")
        assert status_response.json()["status"] == "completed"


@pytest.mark.e2e
class TestMultiDocumentSearchE2E:
    """E2E tests for searching across multiple documents."""

    @pytest.mark.asyncio
    async def test_search_ranks_by_relevance(self, retrieval_client, e2e_db):
        """Search should rank results by relevance."""
        from services.shared.models import Document, Chunk, ProcessingStatus
        from uuid import uuid4

        # Create two documents with different relevance to "CRISPR"
        doc1_id = uuid4()
        doc2_id = uuid4()

        # Doc 1: Highly relevant (mentions CRISPR multiple times)
        doc1 = Document(
            id=doc1_id,
            title="CRISPR-Cas9 Gene Editing Guide",
            abstract="Comprehensive guide to CRISPR technology",
            s3_key="docs/crispr-guide.xml",
            processing_status=ProcessingStatus.COMPLETED,
            has_abstract=True,
            has_full_text=True,
        )

        # Doc 2: Less relevant (mentions CRISPR once)
        doc2 = Document(
            id=doc2_id,
            title="General Biotechnology Methods",
            abstract="Various biotech methods including some gene editing",
            s3_key="docs/biotech-methods.xml",
            processing_status=ProcessingStatus.COMPLETED,
            has_abstract=True,
            has_full_text=True,
        )

        e2e_db.add(doc1)
        e2e_db.add(doc2)
        await e2e_db.flush()

        # Add chunks
        chunk1 = Chunk(
            document_id=doc1_id,
            content="CRISPR-Cas9 is a powerful CRISPR gene editing tool. CRISPR allows precise DNA modifications.",
            section_title="Introduction",
            chunk_index=0,
            token_count=15,
        )

        chunk2 = Chunk(
            document_id=doc2_id,
            content="Various methods exist for gene editing including traditional approaches and CRISPR.",
            section_title="Methods",
            chunk_index=0,
            token_count=12,
        )

        e2e_db.add(chunk1)
        e2e_db.add(chunk2)
        await e2e_db.commit()

        # Search for CRISPR
        response = await retrieval_client.post(
            "/search",
            json={
                "query": "CRISPR gene editing",
                "search_type": "keyword",
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should find both documents
        assert data["total"] >= 2

        # Results should be ordered by relevance score
        if len(data["results"]) >= 2:
            first_score = data["results"][0]["score"]
            second_score = data["results"][1]["score"]
            assert first_score >= second_score


@pytest.mark.e2e
class TestAPIConsistencyE2E:
    """E2E tests for API consistency across services."""

    @pytest.mark.asyncio
    async def test_document_visible_across_services(
        self, ingestion_client, retrieval_client, e2e_db
    ):
        """Document created via ingestion should be visible via retrieval."""
        # Create via ingestion
        ingest_response = await ingestion_client.post(
            "/ingest",
            json={"s3_key": "documents/cross-service-test.xml"},
        )
        doc_id = ingest_response.json()["document_id"]

        # Update to completed status
        from sqlalchemy import update
        from services.shared.models import Document, ProcessingStatus

        await e2e_db.execute(
            update(Document)
            .where(Document.id == UUID(doc_id))
            .values(
                title="Cross-Service Test Document",
                processing_status=ProcessingStatus.COMPLETED,
            )
        )
        await e2e_db.commit()

        # Should be visible via retrieval
        retrieval_response = await retrieval_client.get(f"/documents/{doc_id}")

        assert retrieval_response.status_code == 200
        assert retrieval_response.json()["title"] == "Cross-Service Test Document"

    @pytest.mark.asyncio
    async def test_both_services_healthy(self, ingestion_client, retrieval_client):
        """Both services should report healthy status."""
        ingestion_health = await ingestion_client.get("/health")
        retrieval_health = await retrieval_client.get("/health")

        assert ingestion_health.status_code == 200
        assert retrieval_health.status_code == 200

        assert ingestion_health.json()["status"] == "healthy"
        assert retrieval_health.json()["status"] == "healthy"

        # Both should connect to same database
        assert ingestion_health.json()["database"]["status"] == "healthy"
        assert retrieval_health.json()["database"]["status"] == "healthy"
