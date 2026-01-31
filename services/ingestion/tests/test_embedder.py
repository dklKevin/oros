"""
Tests for embedder module.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestBedrockTitanEmbedder:
    """Tests for BedrockTitanEmbedder."""

    def test_embedder_model_id(self):
        """Should have correct model ID."""
        from services.ingestion.src.embedder import BedrockTitanEmbedder

        embedder = BedrockTitanEmbedder()
        assert embedder.model_id == "amazon.titan-embed-text-v1"

    def test_embedder_dimensions(self):
        """Should have correct dimensions."""
        from services.ingestion.src.embedder import BedrockTitanEmbedder

        embedder = BedrockTitanEmbedder()
        assert embedder.dimensions == 1536

    @patch("boto3.client")
    def test_embed_single(self, mock_boto3_client):
        """Should embed single text correctly."""
        from services.ingestion.src.embedder import BedrockTitanEmbedder
        import json

        # Setup mock response
        mock_client = MagicMock()
        mock_response = {
            "body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps({"embedding": [0.1] * 1536}).encode()
                )
            )
        }
        mock_client.invoke_model.return_value = mock_response
        mock_boto3_client.return_value = mock_client

        embedder = BedrockTitanEmbedder()
        result = embedder.embed_single("Test text")

        assert len(result) == 1536
        mock_client.invoke_model.assert_called_once()

    @patch("boto3.client")
    def test_embed_multiple(self, mock_boto3_client):
        """Should embed multiple texts correctly."""
        from services.ingestion.src.embedder import BedrockTitanEmbedder
        import json

        # Setup mock response
        mock_client = MagicMock()
        mock_response = {
            "body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps({"embedding": [0.1] * 1536}).encode()
                )
            )
        }
        mock_client.invoke_model.return_value = mock_response
        mock_boto3_client.return_value = mock_client

        embedder = BedrockTitanEmbedder()
        result = embedder.embed(["Text 1", "Text 2", "Text 3"])

        assert len(result) == 3
        assert all(len(emb) == 1536 for emb in result)
        assert mock_client.invoke_model.call_count == 3


class TestEmbedder:
    """Tests for main Embedder class."""

    def test_embedder_uses_local_in_dev_without_aws(self):
        """Should use local embedder in dev without AWS credentials."""
        from services.ingestion.src.embedder import Embedder, PaddedLocalEmbedder
        from services.shared.config import Settings

        settings = Settings(
            environment="development",
            aws_access_key_id=None,
            database_url="postgresql://test:test@localhost:5432/test",
        )

        embedder = Embedder(settings=settings)
        # Should use PaddedLocalEmbedder
        assert isinstance(embedder._provider, PaddedLocalEmbedder)

    def test_embedder_uses_bedrock_with_aws(self):
        """Should use Bedrock with AWS credentials."""
        from services.ingestion.src.embedder import Embedder, BedrockTitanEmbedder
        from services.shared.config import Settings

        settings = Settings(
            environment="development",
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
            database_url="postgresql://test:test@localhost:5432/test",
        )

        embedder = Embedder(settings=settings)
        # Should use BedrockTitanEmbedder
        assert isinstance(embedder._provider, BedrockTitanEmbedder)

    def test_embedder_model_id_property(self):
        """Should expose model ID from provider."""
        from services.ingestion.src.embedder import Embedder, BedrockTitanEmbedder
        from services.shared.config import Settings

        settings = Settings(
            environment="development",
            aws_access_key_id="test_key",
            database_url="postgresql://test:test@localhost:5432/test",
        )

        embedder = Embedder(settings=settings)
        assert embedder.model_id == "amazon.titan-embed-text-v1"

    def test_embedder_dimensions_property(self):
        """Should expose dimensions from provider."""
        from services.ingestion.src.embedder import Embedder
        from services.shared.config import Settings

        settings = Settings(
            environment="development",
            aws_access_key_id="test_key",
            database_url="postgresql://test:test@localhost:5432/test",
        )

        embedder = Embedder(settings=settings)
        assert embedder.dimensions == 1536


class TestLocalEmbedder:
    """Tests for LocalEmbedder."""

    def test_local_embedder_model_id(self):
        """Should have correct model ID format."""
        from services.ingestion.src.embedder import LocalEmbedder

        embedder = LocalEmbedder()
        assert "sentence-transformers" in embedder.model_id


class TestPaddedLocalEmbedder:
    """Tests for PaddedLocalEmbedder."""

    def test_padded_embedder_dimensions(self):
        """Should report 1536 dimensions."""
        from services.ingestion.src.embedder import PaddedLocalEmbedder

        embedder = PaddedLocalEmbedder()
        assert embedder.dimensions == 1536


class TestGetEmbedder:
    """Tests for get_embedder factory."""

    def test_get_embedder_returns_embedder(self):
        """Factory should return Embedder instance."""
        from services.ingestion.src.embedder import get_embedder, Embedder

        embedder = get_embedder()
        assert isinstance(embedder, Embedder)
