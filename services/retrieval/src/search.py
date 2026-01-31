"""
Search service for Biomedical Knowledge Platform.

Implements vector, keyword, and hybrid search functionality.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import Settings, get_settings
from services.shared.logging import get_logger
from services.shared.models import Chunk, Document

logger = get_logger(__name__)


@dataclass
class SearchFilters:
    """Filters for search queries."""

    date_from: date | None = None
    date_to: date | None = None
    journals: list[str] | None = None
    article_types: list[str] | None = None


@dataclass
class SearchResult:
    """A single search result."""

    chunk_id: UUID
    document_id: UUID
    title: str
    content: str
    section_title: str | None
    score: float
    authors: list[dict[str, Any]]
    journal: str | None
    publication_date: date | None
    doi: str | None
    pmcid: str | None


@dataclass
class SearchResponse:
    """Response from a search query."""

    results: list[SearchResult]
    total: int
    took_ms: float
    search_type: str


class SearchService:
    """
    Search service implementing vector, keyword, and hybrid search.

    Uses pgvector for vector similarity and PostgreSQL full-text search
    for keyword matching.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        embedder: Any | None = None,
        settings: Settings | None = None,
    ):
        self.db = db_session
        self.settings = settings or get_settings()
        self._embedder = embedder

    @property
    def embedder(self):
        """Lazy initialization of embedder."""
        if self._embedder is None:
            from services.ingestion.src.embedder import get_embedder

            self._embedder = get_embedder(self.settings)
        return self._embedder

    # Maximum query length to prevent abuse
    MAX_QUERY_LENGTH = 10000

    async def search(
        self,
        query: str,
        search_type: str = "hybrid",
        limit: int = 10,
        offset: int = 0,
        filters: SearchFilters | None = None,
        include_context: bool = True,
    ) -> SearchResponse:
        """
        Execute a search query.

        Args:
            query: Search query text
            search_type: One of "vector", "keyword", or "hybrid"
            limit: Maximum number of results
            offset: Offset for pagination
            filters: Optional search filters
            include_context: Whether to include adjacent chunks

        Returns:
            SearchResponse with results and metadata

        Raises:
            ValueError: If query exceeds maximum length
        """
        import time

        # Input validation
        if len(query) > self.MAX_QUERY_LENGTH:
            raise ValueError(f"Query exceeds maximum length of {self.MAX_QUERY_LENGTH} characters")

        start_time = time.time()
        filters = filters or SearchFilters()

        if search_type == "vector":
            results = await self._vector_search(query, limit, offset, filters)
        elif search_type == "keyword":
            results = await self._keyword_search(query, limit, offset, filters)
        else:  # hybrid
            results = await self._hybrid_search(query, limit, offset, filters)

        took_ms = (time.time() - start_time) * 1000

        logger.info(
            "search_completed",
            query=query[:100],
            search_type=search_type,
            results=len(results),
            took_ms=took_ms,
        )

        return SearchResponse(
            results=results,
            total=len(results),  # TODO: Get actual total count
            took_ms=took_ms,
            search_type=search_type,
        )

    async def _vector_search(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: SearchFilters,
    ) -> list[SearchResult]:
        """Perform vector similarity search using pgvector."""
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)

        # Build the vector search query
        # Using pgvector's <=> operator for cosine distance
        stmt = (
            select(
                Chunk,
                Document,
                (1 - Chunk.embedding.cosine_distance(query_embedding)).label("score"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.embedding.isnot(None))
            .where(Document.processing_status == "completed")
        )

        # Apply filters
        stmt = self._apply_filters(stmt, filters)

        # Order by similarity and paginate
        stmt = (
            stmt.order_by(Chunk.embedding.cosine_distance(query_embedding))
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return self._build_results(rows)

    async def _keyword_search(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: SearchFilters,
    ) -> list[SearchResult]:
        """Perform keyword search using PostgreSQL full-text search."""
        # Use PostgreSQL's plainto_tsquery for simple query parsing
        stmt = (
            select(
                Chunk,
                Document,
                func.ts_rank(
                    func.to_tsvector("english", Chunk.content),
                    func.plainto_tsquery("english", query),
                ).label("score"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(
                func.to_tsvector("english", Chunk.content).op("@@")(
                    func.plainto_tsquery("english", query)
                )
            )
            .where(Document.processing_status == "completed")
        )

        # Apply filters
        stmt = self._apply_filters(stmt, filters)

        # Order by rank and paginate
        stmt = (
            stmt.order_by(
                func.ts_rank(
                    func.to_tsvector("english", Chunk.content),
                    func.plainto_tsquery("english", query),
                ).desc()
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return self._build_results(rows)

    async def _hybrid_search(
        self,
        query: str,
        limit: int,
        offset: int,
        filters: SearchFilters,
    ) -> list[SearchResult]:
        """
        Perform hybrid search using the hybrid_search SQL function.

        Combines vector and keyword search using Reciprocal Rank Fusion (RRF).
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)

        # Convert embedding to PostgreSQL vector literal string
        # asyncpg needs the embedding as a string for proper type casting
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Convert filters to SQL parameters
        filter_journals = filters.journals if filters.journals else None
        filter_date_from = filters.date_from
        filter_date_to = filters.date_to

        # Use the hybrid_search function defined in init-db.sql
        # Note: We use CAST() instead of ::vector to avoid asyncpg parameter binding issues
        stmt = text("""
            SELECT
                hs.chunk_id,
                hs.document_id,
                hs.content,
                hs.section_title,
                hs.rrf_score as score,
                hs.vector_similarity,
                d.title,
                d.authors,
                d.journal,
                d.publication_date,
                d.doi,
                d.pmcid
            FROM hybrid_search(
                CAST(:query_embedding AS vector),
                :query_text,
                :match_count,
                :vector_weight,
                :keyword_weight,
                :filter_journals,
                :filter_date_from,
                :filter_date_to
            ) hs
            JOIN documents d ON hs.document_id = d.id
            OFFSET :offset
        """)

        result = await self.db.execute(
            stmt,
            {
                "query_embedding": embedding_str,
                "query_text": query,
                "match_count": limit + offset,
                "vector_weight": self.settings.search_vector_weight,
                "keyword_weight": self.settings.search_keyword_weight,
                "filter_journals": filter_journals,
                "filter_date_from": filter_date_from,
                "filter_date_to": filter_date_to,
                "offset": offset,
            },
        )
        rows = result.fetchall()

        # Build results from raw SQL results
        results = []
        for row in rows:
            results.append(
                SearchResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    title=row.title,
                    content=row.content,
                    section_title=row.section_title,
                    score=float(row.score),
                    authors=row.authors or [],
                    journal=row.journal,
                    publication_date=row.publication_date,
                    doi=row.doi,
                    pmcid=row.pmcid,
                )
            )

        return results

    def _apply_filters(self, stmt, filters: SearchFilters):
        """Apply filters to a SQLAlchemy statement."""
        if filters.date_from:
            stmt = stmt.where(Document.publication_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(Document.publication_date <= filters.date_to)
        if filters.journals:
            stmt = stmt.where(Document.journal.in_(filters.journals))
        if filters.article_types:
            stmt = stmt.where(Document.article_type.in_(filters.article_types))
        return stmt

    def _build_results(self, rows) -> list[SearchResult]:
        """Build SearchResult objects from query results."""
        results = []
        for row in rows:
            chunk = row.Chunk
            document = row.Document
            score = row.score

            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    title=document.title,
                    content=chunk.content,
                    section_title=chunk.section_title,
                    score=float(score),
                    authors=document.authors or [],
                    journal=document.journal,
                    publication_date=document.publication_date,
                    doi=document.doi,
                    pmcid=document.pmcid,
                )
            )

        return results

    async def get_document(self, document_id: UUID) -> Document | None:
        """Get a document by ID."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_document_chunks(
        self,
        document_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Chunk], int]:
        """Get chunks for a document."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
        )
        total = count_result.scalar() or 0

        # Get chunks
        result = await self.db.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .offset(offset)
            .limit(limit)
        )
        chunks = result.scalars().all()

        return list(chunks), total


def get_search_service(
    db_session: AsyncSession,
    settings: Settings | None = None,
) -> SearchService:
    """Factory function to get a configured search service."""
    return SearchService(db_session=db_session, settings=settings)
