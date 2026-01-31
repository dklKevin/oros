"""
SQLAlchemy ORM models for documents and chunks.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.shared.database import Base


class ProcessingStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(str, Enum):
    """Processing job types."""

    INGESTION = "ingestion"
    EMBEDDING = "embedding"
    REINDEX = "reindex"


class SearchType(str, Enum):
    """Search types."""

    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class Document(Base):
    """
    Represents a biomedical document (paper, article).

    Stores metadata and references to the full content in S3.
    """

    __tablename__ = "documents"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Core metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    journal: Mapped[str | None] = mapped_column(String(500))
    publication_date: Mapped[date | None] = mapped_column(Date)

    # Identifiers
    doi: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    pmcid: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    pmid: Mapped[str | None] = mapped_column(String(50))

    # Classification
    mesh_terms: Mapped[list[str]] = mapped_column(JSONB, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    article_type: Mapped[str | None] = mapped_column(String(100))

    # Source and storage
    source_url: Mapped[str | None] = mapped_column(Text)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    s3_bucket: Mapped[str | None] = mapped_column(String(255))

    # Processing status
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        String(20), default=ProcessingStatus.PENDING
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Quality metrics
    quality_score: Mapped[float | None] = mapped_column(Float)
    has_abstract: Mapped[bool] = mapped_column(Boolean, default=False)
    has_full_text: Mapped[bool] = mapped_column(Boolean, default=False)
    section_count: Mapped[int] = mapped_column(Integer, default=0)
    reference_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    # Flags
    retracted: Mapped[bool] = mapped_column(Boolean, default=False)
    retraction_date: Mapped[date | None] = mapped_column(Date)
    retraction_reason: Mapped[str | None] = mapped_column(Text)

    # Additional metadata (named extra_metadata to avoid SQLAlchemy reserved name)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )

    def calculate_quality_score(self) -> float:
        """Calculate quality score based on document completeness."""
        score = 0.0

        if self.has_abstract:
            score += 0.3
        if self.has_full_text:
            score += 0.3
        if self.section_count:
            score += min(self.section_count / 5.0, 1.0) * 0.2
        if self.reference_count:
            score += min(self.reference_count / 20.0, 1.0) * 0.2

        return round(score, 2)

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title[:50]}...', status={self.processing_status})>"


class Chunk(Base):
    """
    Represents a chunk of text from a document with its embedding.

    Chunks are the basic unit for vector search.
    """

    __tablename__ = "chunks"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign key to document
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)

    # Position and structure
    section_title: Mapped[str | None] = mapped_column(String(500))
    section_type: Mapped[str | None] = mapped_column(String(100))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)

    # Token information
    token_count: Mapped[int | None] = mapped_column(Integer)

    # Embedding with versioning (1536 dimensions for Bedrock Titan)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    embedding_model_id: Mapped[str | None] = mapped_column(String(100))
    embedding_version: Mapped[int] = mapped_column(Integer, default=1)
    embedding_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Chunk relationships
    previous_chunk_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL")
    )
    next_chunk_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL")
    )

    # Additional metadata (named extra_metadata to avoid SQLAlchemy reserved name)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<Chunk(id={self.id}, doc={self.document_id}, index={self.chunk_index})>"


class ProcessingJob(Base):
    """
    Tracks async processing jobs for documents.
    """

    __tablename__ = "processing_jobs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign key to document
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )

    # Job details
    job_type: Mapped[JobType] = mapped_column(String(50), nullable=False)
    status: Mapped[ProcessingStatus] = mapped_column(
        String(20), default=ProcessingStatus.PENDING
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Progress tracking
    total_steps: Mapped[int | None] = mapped_column(Integer)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String(255))

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # SQS integration
    sqs_message_id: Mapped[str | None] = mapped_column(String(255))
    sqs_receipt_handle: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Additional metadata (named extra_metadata to avoid SQLAlchemy reserved name)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="processing_jobs"
    )

    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, type={self.job_type}, status={self.status})>"


class SearchHistory(Base):
    """
    Records search queries for analytics and optimization.
    """

    __tablename__ = "search_history"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Query details
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    search_type: Mapped[SearchType] = mapped_column(String(20), nullable=False)

    # Filters applied
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Results
    result_count: Mapped[int | None] = mapped_column(Integer)
    result_ids: Mapped[list[UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))

    # Performance
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    # User context
    user_id: Mapped[str | None] = mapped_column(String(255))
    session_id: Mapped[str | None] = mapped_column(String(255))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<SearchHistory(id={self.id}, query='{self.query_text[:30]}...', type={self.search_type})>"


# Table indexes (defined in init-db.sql, but also declared here for clarity)
Index("idx_documents_publication_date", Document.publication_date)
Index("idx_chunks_document_chunk", Chunk.document_id, Chunk.chunk_index)
