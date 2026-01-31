"""
Tests for document processor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.ingestion.src.processor import ProcessingResult, DocumentProcessor


class TestProcessingResult:
    """Tests for ProcessingResult class."""

    def test_result_creation_success(self):
        """Should create successful result."""
        doc_id = uuid4()
        result = ProcessingResult(
            document_id=doc_id,
            success=True,
            chunks_created=10,
        )
        assert result.document_id == doc_id
        assert result.success is True
        assert result.chunks_created == 10
        assert result.error_message is None

    def test_result_creation_failure(self):
        """Should create failure result with error."""
        doc_id = uuid4()
        result = ProcessingResult(
            document_id=doc_id,
            success=False,
            error_message="Parse error",
            error_details={"line": 42},
        )
        assert result.success is False
        assert result.error_message == "Parse error"
        assert result.error_details["line"] == 42

    def test_result_default_values(self):
        """Should have sensible defaults."""
        doc_id = uuid4()
        result = ProcessingResult(document_id=doc_id, success=True)
        assert result.chunks_created == 0
        assert result.error_details == {}


class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_s3_client(self):
        """Create mock S3 client."""
        client = MagicMock()
        client.download_file = AsyncMock(return_value=b"test content")
        client.upload_file = AsyncMock()
        return client

    @pytest.fixture
    def mock_embedder(self):
        """Create mock embedder."""
        embedder = MagicMock()
        embedder.embed_texts = MagicMock(return_value=[[0.1] * 1536])
        embedder.model_id = "test-model"
        embedder.dimensions = 1536
        return embedder

    def test_processor_initialization(self, mock_db_session):
        """Should initialize with required dependencies."""
        processor = DocumentProcessor(
            db_session=mock_db_session,
        )
        assert processor.db == mock_db_session
        assert processor.settings is not None
        assert len(processor.parsers) >= 1

    def test_processor_with_custom_settings(self, mock_db_session):
        """Should accept custom settings."""
        from services.shared.config import Settings

        settings = Settings(
            environment="development",
            database_url="postgresql://test:test@localhost:5432/test",
            chunk_max_tokens=256,
            chunk_overlap_tokens=50,
        )

        processor = DocumentProcessor(
            db_session=mock_db_session,
            settings=settings,
        )

        assert processor.settings.chunk_max_tokens == 256
        assert processor.settings.chunk_overlap_tokens == 50

    def test_processor_has_parsers(self, mock_db_session):
        """Should have at least one parser."""
        processor = DocumentProcessor(db_session=mock_db_session)
        assert len(processor.parsers) > 0

    def test_processor_has_chunker(self, mock_db_session):
        """Should have a chunker initialized."""
        processor = DocumentProcessor(db_session=mock_db_session)
        assert processor.chunker is not None


class TestDocumentProcessorParsing:
    """Tests for parsing functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        return session

    def test_find_parser_for_xml(self, mock_db_session):
        """Should find XML parser for XML content."""
        processor = DocumentProcessor(db_session=mock_db_session)

        xml_content = b'<?xml version="1.0"?><article></article>'
        parser = None
        for p in processor.parsers:
            if p.can_parse(xml_content, filename="test.xml"):
                parser = p
                break

        assert parser is not None

    def test_no_parser_for_unknown_format(self, mock_db_session):
        """Should not find parser for unknown format."""
        processor = DocumentProcessor(db_session=mock_db_session)

        unknown_content = b"some random binary content"
        parser = None
        for p in processor.parsers:
            if p.can_parse(unknown_content, filename="test.bin"):
                parser = p
                break

        assert parser is None
