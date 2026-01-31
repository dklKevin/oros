"""
Chunking strategies for document processing.

Implements section-aware chunking that preserves document structure
while maintaining appropriate chunk sizes for embedding.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any

import tiktoken

from services.shared.config import get_settings
from services.shared.logging import get_logger
from services.ingestion.src.parsers.base import ParsedDocument, Section

logger = get_logger(__name__)


@dataclass
class Chunk:
    """Represents a chunk of text ready for embedding."""

    content: str
    chunk_index: int

    # Source information
    section_title: str | None = None
    section_type: str | None = None
    page_number: int | None = None

    # Token information
    token_count: int = 0

    # Hash for deduplication
    content_hash: str = ""

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute content hash after initialization."""
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.content.encode("utf-8")
            ).hexdigest()


class ChunkingStrategy:
    """Base class for chunking strategies."""

    def __init__(
        self,
        max_tokens: int | None = None,
        overlap_tokens: int | None = None,
        tokenizer_name: str = "cl100k_base",
    ):
        settings = get_settings()
        self.max_tokens = max_tokens or settings.chunk_max_tokens
        self.overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens
        self.tokenizer = tiktoken.get_encoding(tokenizer_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Chunk a document. Override in subclasses."""
        raise NotImplementedError


class SectionAwareChunker(ChunkingStrategy):
    """
    Section-aware chunking strategy.

    Preserves document structure by:
    1. Using section boundaries as natural break points
    2. Applying secondary chunking within long sections
    3. Maintaining overlap between chunks for context
    """

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """
        Chunk a document while preserving section structure.

        Args:
            document: Parsed document to chunk

        Returns:
            List of chunks with metadata
        """
        chunks: list[Chunk] = []
        chunk_index = 0

        # First, chunk the abstract if present
        if document.abstract:
            abstract_chunks = self._chunk_text(
                text=document.abstract,
                section_title="Abstract",
                section_type="abstract",
                start_index=chunk_index,
            )
            chunks.extend(abstract_chunks)
            chunk_index += len(abstract_chunks)

        # Then chunk each section
        for section in document.sections:
            section_chunks = self._chunk_section(
                section=section,
                start_index=chunk_index,
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        logger.info(
            "document_chunked",
            total_chunks=len(chunks),
            total_tokens=sum(c.token_count for c in chunks),
            sections=len(document.sections),
        )

        return chunks

    def _chunk_section(
        self,
        section: Section,
        start_index: int,
        parent_title: str | None = None,
    ) -> list[Chunk]:
        """Recursively chunk a section and its subsections."""
        chunks: list[Chunk] = []

        # Build full section title
        if parent_title:
            full_title = f"{parent_title} > {section.title}"
        else:
            full_title = section.title

        # Chunk the section content
        if section.content.strip():
            content_chunks = self._chunk_text(
                text=section.content,
                section_title=full_title,
                section_type=section.section_type,
                start_index=start_index,
            )
            chunks.extend(content_chunks)

        # Recursively chunk subsections
        for subsection in section.subsections:
            sub_chunks = self._chunk_section(
                section=subsection,
                start_index=start_index + len(chunks),
                parent_title=full_title,
            )
            chunks.extend(sub_chunks)

        return chunks

    def _chunk_text(
        self,
        text: str,
        section_title: str | None,
        section_type: str | None,
        start_index: int,
    ) -> list[Chunk]:
        """
        Chunk a piece of text with overlap.

        Uses a sliding window approach with paragraph-aware splitting.
        """
        chunks: list[Chunk] = []

        # Clean and normalize text
        text = text.strip()
        if not text:
            return chunks

        # Count tokens
        total_tokens = self.count_tokens(text)

        # If text fits in one chunk, return it directly
        if total_tokens <= self.max_tokens:
            chunks.append(Chunk(
                content=text,
                chunk_index=start_index,
                section_title=section_title,
                section_type=section_type,
                token_count=total_tokens,
            ))
            return chunks

        # Split into paragraphs first
        paragraphs = self._split_into_paragraphs(text)

        # Build chunks from paragraphs
        current_chunk_parts: list[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            para_tokens = self.count_tokens(paragraph)

            # If single paragraph exceeds max tokens, split it further
            if para_tokens > self.max_tokens:
                # Flush current chunk first
                if current_chunk_parts:
                    chunk_text = "\n\n".join(current_chunk_parts)
                    chunks.append(Chunk(
                        content=chunk_text,
                        chunk_index=start_index + len(chunks),
                        section_title=section_title,
                        section_type=section_type,
                        token_count=self.count_tokens(chunk_text),
                    ))
                    current_chunk_parts = []
                    current_tokens = 0

                # Split long paragraph by sentences
                sentence_chunks = self._split_long_text(paragraph)
                for sent_chunk in sentence_chunks:
                    chunks.append(Chunk(
                        content=sent_chunk,
                        chunk_index=start_index + len(chunks),
                        section_title=section_title,
                        section_type=section_type,
                        token_count=self.count_tokens(sent_chunk),
                    ))
                continue

            # Check if adding this paragraph would exceed limit
            if current_tokens + para_tokens > self.max_tokens:
                # Save current chunk
                if current_chunk_parts:
                    chunk_text = "\n\n".join(current_chunk_parts)
                    chunks.append(Chunk(
                        content=chunk_text,
                        chunk_index=start_index + len(chunks),
                        section_title=section_title,
                        section_type=section_type,
                        token_count=self.count_tokens(chunk_text),
                    ))

                    # Start new chunk with overlap
                    overlap_parts = self._get_overlap_parts(
                        current_chunk_parts, self.overlap_tokens
                    )
                    current_chunk_parts = overlap_parts
                    current_tokens = sum(
                        self.count_tokens(p) for p in current_chunk_parts
                    )

            # Add paragraph to current chunk
            current_chunk_parts.append(paragraph)
            current_tokens += para_tokens

        # Don't forget the last chunk
        if current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts)
            chunks.append(Chunk(
                content=chunk_text,
                chunk_index=start_index + len(chunks),
                section_title=section_title,
                section_type=section_type,
                token_count=self.count_tokens(chunk_text),
            ))

        return chunks

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines or single newlines with empty content
        paragraphs = []
        for para in text.split("\n\n"):
            para = para.strip()
            if para:
                paragraphs.append(para)
        return paragraphs

    def _split_long_text(self, text: str) -> list[str]:
        """Split very long text (longer than max_tokens) into smaller pieces."""
        chunks = []
        tokens = self.tokenizer.encode(text)

        start = 0
        while start < len(tokens):
            # Take max_tokens worth
            end = min(start + self.max_tokens, len(tokens))

            # Decode this chunk
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text.strip())

            # Move start with overlap
            start = end - self.overlap_tokens

        return chunks

    def _get_overlap_parts(
        self, parts: list[str], target_tokens: int
    ) -> list[str]:
        """Get parts from the end that sum to approximately target_tokens."""
        if not parts or target_tokens <= 0:
            return []

        overlap_parts = []
        total_tokens = 0

        # Work backwards through parts
        for part in reversed(parts):
            part_tokens = self.count_tokens(part)
            if total_tokens + part_tokens > target_tokens:
                break
            overlap_parts.insert(0, part)
            total_tokens += part_tokens

        return overlap_parts


class FixedSizeChunker(ChunkingStrategy):
    """
    Simple fixed-size chunking with overlap.

    Ignores document structure, useful for fallback or simple use cases.
    """

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Chunk document using fixed-size windows."""
        chunks: list[Chunk] = []
        text = document.full_text

        # Split into chunks using token-based sliding window
        tokens = self.tokenizer.encode(text)
        chunk_index = 0
        start = 0

        while start < len(tokens):
            end = min(start + self.max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens).strip()

            if chunk_text:
                chunks.append(Chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    token_count=len(chunk_tokens),
                ))
                chunk_index += 1

            # Move start with overlap
            start = end - self.overlap_tokens
            if start >= len(tokens) - self.overlap_tokens:
                break

        return chunks
