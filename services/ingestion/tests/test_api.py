"""
Tests for Ingestion Service API endpoints.

These tests verify the API behavior using TestClient.
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
        assert data["service"] == "ingestion"
        assert "database" in data


class TestIngestEndpoint:
    """Tests for /ingest endpoint."""

    def test_ingest_requires_source_url_or_s3_key(self, client: TestClient):
        """Ingest should fail if neither source_url nor s3_key provided."""
        response = client.post("/ingest", json={})

        assert response.status_code == 400
        assert "source_url or s3_key" in response.json()["detail"].lower()

    def test_ingest_accepts_s3_key(self, client: TestClient):
        """Ingest should accept s3_key and return job info."""
        response = client.post(
            "/ingest",
            json={
                "s3_key": "documents/test.xml",
                "document_type": "pubmed_xml",
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert "document_id" in data
        assert data["status"] == "queued"
        # Verify UUIDs are valid
        uuid4_from_str = lambda s: len(s) == 36 and s.count("-") == 4
        assert uuid4_from_str(data["job_id"])
        assert uuid4_from_str(data["document_id"])

    def test_ingest_accepts_source_url(self, client: TestClient):
        """Ingest should accept source_url and return job info."""
        response = client.post(
            "/ingest",
            json={
                "source_url": "https://example.com/paper.xml",
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert "document_id" in data


class TestStatusEndpoint:
    """Tests for /status/{job_id} endpoint."""

    def test_status_returns_404_for_missing_job(self, client: TestClient):
        """Status should return 404 for non-existent job."""
        job_id = str(uuid4())

        response = client.get(f"/status/{job_id}")

        assert response.status_code == 404

    def test_status_returns_400_for_invalid_uuid(self, client: TestClient):
        """Status should return 400 for invalid job ID format."""
        response = client.get("/status/not-a-uuid")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_status_returns_job_info_after_ingest(self, client: TestClient):
        """Status should return job info for a job that was created via ingest."""
        # First create a job via ingest
        ingest_response = client.post(
            "/ingest",
            json={"s3_key": "documents/test.xml"},
        )
        assert ingest_response.status_code == 202
        job_id = ingest_response.json()["job_id"]

        # Then check its status
        response = client.get(f"/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "completed_steps" in data
