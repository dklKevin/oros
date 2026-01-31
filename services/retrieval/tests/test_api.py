"""
Tests for Retrieval Service API endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_healthy_when_db_connected(self, client: TestClient):
        """Health check should return healthy status when database is connected."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "retrieval"
        assert "database" in data


class TestSearchEndpoint:
    """Tests for /search endpoint."""

    def test_search_requires_query(self, client: TestClient):
        """Search should fail without a query."""
        response = client.post("/search", json={})

        assert response.status_code == 422  # Validation error

    def test_search_returns_results_structure(self, client: TestClient):
        """Search should return properly structured results."""
        response = client.post(
            "/search",
            json={
                "query": "CRISPR gene editing",
                "search_type": "hybrid",
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query_metadata" in data
        assert isinstance(data["results"], list)

    def test_search_respects_limit(self, client: TestClient):
        """Search should respect the limit parameter."""
        response = client.post(
            "/search",
            json={
                "query": "gene therapy",
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5

    def test_search_supports_vector_type(self, client: TestClient):
        """Search should support vector search type."""
        response = client.post(
            "/search",
            json={
                "query": "tissue engineering",
                "search_type": "vector",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query_metadata"]["retrieval_strategy"] == "vector"

    def test_search_supports_keyword_type(self, client: TestClient):
        """Search should support keyword search type."""
        response = client.post(
            "/search",
            json={
                "query": "biosensor",
                "search_type": "keyword",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query_metadata"]["retrieval_strategy"] == "keyword"


class TestDocumentsEndpoint:
    """Tests for /documents endpoints."""

    def test_get_document_returns_404_for_missing(self, client: TestClient):
        """Get document should return 404 for non-existent document."""
        doc_id = str(uuid4())
        response = client.get(f"/documents/{doc_id}")

        assert response.status_code == 404

    def test_get_document_chunks_returns_structure(self, client: TestClient):
        """Get document chunks should return proper structure."""
        doc_id = str(uuid4())
        response = client.get(f"/documents/{doc_id}/chunks")

        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert "chunks" in data
        assert "total" in data
        assert isinstance(data["chunks"], list)


class TestChatEndpoint:
    """Tests for /chat endpoint."""

    def test_chat_requires_query(self, client: TestClient):
        """Chat should fail without a query."""
        response = client.post("/chat", json={})

        assert response.status_code == 422  # Validation error

    def test_chat_returns_answer_structure(self, client: TestClient):
        """Chat should return properly structured response."""
        response = client.post(
            "/chat",
            json={
                "query": "What is CRISPR?",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "confidence_score" in data
        assert "query_metadata" in data
