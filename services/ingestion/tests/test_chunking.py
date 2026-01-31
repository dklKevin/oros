"""
Tests for chunking strategies.
"""

import pytest
from unittest.mock import MagicMock, patch
from services.ingestion.src.chunking.strategies import (
    Chunk,
)


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_chunk_creation(self):
        """Chunk should be created with required fields."""
        chunk = Chunk(
            content="Test content",
            chunk_index=0,
        )
        assert chunk.content == "Test content"
        assert chunk.chunk_index == 0

    def test_chunk_computes_hash(self):
        """Chunk should compute content hash on creation."""
        chunk = Chunk(
            content="Test content",
            chunk_index=0,
        )
        assert chunk.content_hash != ""
        assert len(chunk.content_hash) == 64  # SHA256 hex digest

    def test_chunk_same_content_same_hash(self):
        """Same content should produce same hash."""
        chunk1 = Chunk(content="Same content", chunk_index=0)
        chunk2 = Chunk(content="Same content", chunk_index=1)
        assert chunk1.content_hash == chunk2.content_hash

    def test_chunk_different_content_different_hash(self):
        """Different content should produce different hash."""
        chunk1 = Chunk(content="Content A", chunk_index=0)
        chunk2 = Chunk(content="Content B", chunk_index=0)
        assert chunk1.content_hash != chunk2.content_hash

    def test_chunk_with_metadata(self):
        """Chunk should accept metadata."""
        chunk = Chunk(
            content="Test",
            chunk_index=0,
            section_title="Introduction",
            section_type="text",
            page_number=1,
            metadata={"key": "value"},
        )
        assert chunk.section_title == "Introduction"
        assert chunk.section_type == "text"
        assert chunk.page_number == 1
        assert chunk.metadata == {"key": "value"}

    def test_chunk_with_token_count(self):
        """Chunk should accept token_count."""
        chunk = Chunk(
            content="Test content",
            chunk_index=0,
            token_count=5,
        )
        assert chunk.token_count == 5

    def test_chunk_default_values(self):
        """Chunk should have sensible defaults."""
        chunk = Chunk(content="Test", chunk_index=0)
        assert chunk.section_title is None
        assert chunk.section_type is None
        assert chunk.page_number is None
        assert chunk.token_count == 0
        assert chunk.metadata == {}
