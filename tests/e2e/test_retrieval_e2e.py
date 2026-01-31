"""
E2E Tests for Retrieval Service.

Tests the complete retrieval flow against a real PostgreSQL database.
"""

import pytest
from uuid import UUID


@pytest.mark.e2e
class TestRetrievalHealthE2E:
    """E2E tests for retrieval service health."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, retrieval_client):
        """Health endpoint should return healthy when connected to real DB."""
        response = await retrieval_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "retrieval"
        assert "database" in data


@pytest.mark.e2e
class TestSearchE2E:
    """E2E tests for search endpoint."""

    @pytest.mark.asyncio
    async def test_search_empty_database(self, retrieval_client):
        """Search on empty database should return empty results."""
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
        assert data["results"] == []
        assert data["total"] == 0
        assert "query_metadata" in data

    @pytest.mark.asyncio
    async def test_search_with_data(self, retrieval_client, sample_document, sample_chunks):
        """Search should return results when data exists."""
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

        # Should find chunks containing "CRISPR"
        assert data["total"] >= 1
        assert len(data["results"]) >= 1

        # Verify result structure
        result = data["results"][0]
        assert "chunk_id" in result
        assert "document_id" in result
        assert "content" in result
        assert "score" in result

    @pytest.mark.asyncio
    async def test_search_keyword_type(self, retrieval_client, sample_document, sample_chunks):
        """Keyword search should use full-text search."""
        response = await retrieval_client.post(
            "/search",
            json={
                "query": "cardiovascular disease",
                "search_type": "keyword",
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query_metadata"]["retrieval_strategy"] == "keyword"

    @pytest.mark.asyncio
    async def test_search_with_date_filter(self, retrieval_client, sample_document, sample_chunks):
        """Search should respect date filters."""
        response = await retrieval_client.post(
            "/search",
            json={
                "query": "gene therapy",
                "search_type": "keyword",
                "filters": {
                    "date_from": "2024-01-01",
                    "date_to": "2024-12-31",
                },
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "filters_applied" in data["query_metadata"]

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, retrieval_client, sample_document, sample_chunks):
        """Search should respect the limit parameter."""
        response = await retrieval_client.post(
            "/search",
            json={
                "query": "gene",
                "search_type": "keyword",
                "limit": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 2


@pytest.mark.e2e
class TestDocumentsE2E:
    """E2E tests for document endpoints."""

    @pytest.mark.asyncio
    async def test_get_document_by_id(self, retrieval_client, sample_document):
        """GET /documents/{id} should return document metadata."""
        doc_id = str(sample_document["id"])
        response = await retrieval_client.get(f"/documents/{doc_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["title"] == sample_document["title"]
        assert data["doi"] == sample_document["doi"]

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, retrieval_client):
        """GET /documents/{id} should return 404 for unknown document."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await retrieval_client.get(f"/documents/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_document_chunks(self, retrieval_client, sample_document, sample_chunks):
        """GET /documents/{id}/chunks should return document chunks."""
        doc_id = str(sample_document["id"])
        response = await retrieval_client.get(f"/documents/{doc_id}/chunks")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert len(data["chunks"]) == len(sample_chunks)
        assert data["total"] == len(sample_chunks)

        # Verify chunk structure
        chunk = data["chunks"][0]
        assert "id" in chunk
        assert "content" in chunk
        assert "section_title" in chunk

    @pytest.mark.asyncio
    async def test_get_document_chunks_pagination(
        self, retrieval_client, sample_document, sample_chunks
    ):
        """GET /documents/{id}/chunks should support pagination."""
        doc_id = str(sample_document["id"])
        response = await retrieval_client.get(
            f"/documents/{doc_id}/chunks",
            params={"limit": 1, "offset": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["chunks"]) == 1
        assert data["total"] == len(sample_chunks)
        assert data["limit"] == 1
        assert data["offset"] == 0


@pytest.mark.e2e
class TestChatE2E:
    """E2E tests for chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_empty_database(self, retrieval_client):
        """Chat on empty database should return 'no information' response."""
        response = await retrieval_client.post(
            "/chat",
            json={
                "query": "What is CRISPR?",
                "max_chunks": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["citations"] == []
        assert data["confidence_score"] == 0.0
        # Should indicate no information found
        assert "couldn't find" in data["answer"].lower() or data["chunks_used"] == 0

    @pytest.mark.asyncio
    async def test_chat_requires_query(self, retrieval_client):
        """POST /chat should require query field."""
        response = await retrieval_client.post("/chat", json={})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_chat_response_structure(self, retrieval_client):
        """Chat response should have proper structure."""
        response = await retrieval_client.post(
            "/chat",
            json={
                "query": "Tell me about gene therapy",
                "max_chunks": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "citations" in data
        assert "confidence_score" in data
        assert "query_metadata" in data
        assert "took_ms" in data["query_metadata"]
        assert "chunks_used" in data["query_metadata"]
        assert "model" in data["query_metadata"]
