"""
Retrieval Service - FastAPI Application Entry Point.

Provides endpoints for search and RAG-powered chat.
"""

from contextlib import asynccontextmanager
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import get_settings
from services.shared.database import close_db, get_db, health_check as db_health_check, init_db
from services.shared.logging import configure_logging, get_logger, LoggingMiddleware
from services.shared.rate_limiter import rate_limit, RateLimitMiddleware
from services.retrieval.src.search import SearchService, SearchFilters as SearchFiltersData
from services.retrieval.src.rag import RAGService

settings = get_settings()
configure_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    service_name="retrieval-service",
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("starting_retrieval_service", environment=settings.environment)
    await init_db()
    yield
    # Shutdown
    logger.info("stopping_retrieval_service")
    await close_db()


app = FastAPI(
    title="Oros - Retrieval Service",
    description="Semantic search and RAG-powered chat for biomedical literature",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(LoggingMiddleware, service_name="retrieval-service")
app.add_middleware(RateLimitMiddleware)

# CORS configuration - explicit allowed origins only
# Never use allow_origins=["*"] with allow_credentials=True
ALLOWED_ORIGINS = (
    ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"]
    if settings.is_development
    else []  # Configure via environment in production
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True if ALLOWED_ORIGINS else False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# =============================================================================
# Request/Response Models
# =============================================================================
class SearchFilters(BaseModel):
    """Filters for search queries."""

    date_from: date | None = Field(None, description="Filter by publication date (from)")
    date_to: date | None = Field(None, description="Filter by publication date (to)")
    journals: list[str] | None = Field(None, description="Filter by journal names")
    article_types: list[str] | None = Field(None, description="Filter by article types")


class SearchRequest(BaseModel):
    """Request model for search."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    search_type: str = Field("hybrid", description="Search type: vector, keyword, or hybrid")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    include_context: bool = Field(True, description="Include adjacent chunks for context")


class ChunkMetadata(BaseModel):
    """Metadata for a search result chunk."""

    authors: list[str] = []
    journal: str | None = None
    publication_date: date | None = None
    doi: str | None = None
    pmcid: str | None = None


class ChunkContext(BaseModel):
    """Context from adjacent chunks."""

    previous_chunk: str | None = None
    next_chunk: str | None = None


class SearchResult(BaseModel):
    """A single search result."""

    chunk_id: UUID
    document_id: UUID
    title: str
    content: str
    section_title: str | None
    score: float
    metadata: ChunkMetadata
    context: ChunkContext | None = None


class SearchResponse(BaseModel):
    """Response model for search."""

    results: list[SearchResult]
    total: int
    query_metadata: dict[str, Any]


class ChatRequest(BaseModel):
    """Request model for RAG chat."""

    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list, description="Previous messages in conversation"
    )
    max_chunks: int = Field(5, ge=1, le=20, description="Maximum chunks to use for context")


class Citation(BaseModel):
    """Citation for a RAG response."""

    chunk_id: UUID
    document_id: UUID
    title: str
    doi: str | None
    pmcid: str | None
    relevance_score: float


class ChatResponse(BaseModel):
    """Response model for RAG chat."""

    answer: str
    citations: list[Citation]
    confidence_score: float
    query_metadata: dict[str, Any]


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    service: str
    database: dict[str, Any]


# =============================================================================
# Endpoints
# =============================================================================
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns service and dependency health status.
    """
    db_status = await db_health_check()
    overall_status = "healthy" if db_status["status"] == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        service="retrieval",
        database=db_status,
    )


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(rate_limit(limit=settings.rate_limit_search_per_minute, window_seconds=60)),
) -> SearchResponse:
    """
    Search the biomedical knowledge base.

    Supports vector, keyword, and hybrid search modes with filtering.
    """
    logger.info(
        "search_requested",
        query=request.query[:100],
        search_type=request.search_type,
        limit=request.limit,
    )

    # Convert API filters to service filters
    filters = SearchFiltersData(
        date_from=request.filters.date_from,
        date_to=request.filters.date_to,
        journals=request.filters.journals,
        article_types=request.filters.article_types,
    )

    # Execute search
    search_service = SearchService(db_session=db, settings=settings)
    search_response = await search_service.search(
        query=request.query,
        search_type=request.search_type,
        limit=request.limit,
        offset=request.offset,
        filters=filters,
        include_context=request.include_context,
    )

    # Convert service results to API response
    results = []
    for result in search_response.results:
        # Extract author names from author dicts
        author_names = []
        for author in result.authors:
            if isinstance(author, dict):
                name_parts = []
                if author.get("given_names"):
                    name_parts.append(author["given_names"])
                if author.get("surname"):
                    name_parts.append(author["surname"])
                author_names.append(" ".join(name_parts))
            else:
                author_names.append(str(author))

        results.append(
            SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                title=result.title,
                content=result.content,
                section_title=result.section_title,
                score=result.score,
                metadata=ChunkMetadata(
                    authors=author_names,
                    journal=result.journal,
                    publication_date=result.publication_date,
                    doi=result.doi,
                    pmcid=result.pmcid,
                ),
                context=None,  # TODO: Implement context fetching
            )
        )

    return SearchResponse(
        results=results,
        total=search_response.total,
        query_metadata={
            "took_ms": search_response.took_ms,
            "retrieval_strategy": search_response.search_type,
            "filters_applied": request.filters.model_dump(exclude_none=True),
        },
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(rate_limit(limit=settings.rate_limit_chat_per_minute, window_seconds=60)),
) -> ChatResponse:
    """
    RAG-powered chat endpoint.

    Retrieves relevant context and generates an answer with citations.
    """
    logger.info(
        "chat_requested",
        query=request.query[:100],
        history_length=len(request.conversation_history),
    )

    # Convert API filters to service filters
    filters = SearchFiltersData(
        date_from=request.filters.date_from,
        date_to=request.filters.date_to,
        journals=request.filters.journals,
        article_types=request.filters.article_types,
    )

    # Execute RAG query
    rag_service = RAGService(db_session=db, settings=settings)
    rag_response = await rag_service.answer(
        query=request.query,
        filters=filters,
        conversation_history=request.conversation_history,
        max_chunks=request.max_chunks,
    )

    # Convert to API response
    citations = [
        Citation(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            title=c.title,
            doi=c.doi,
            pmcid=c.pmcid,
            relevance_score=c.relevance_score,
        )
        for c in rag_response.citations
    ]

    return ChatResponse(
        answer=rag_response.answer,
        citations=citations,
        confidence_score=rag_response.confidence_score,
        query_metadata={
            "took_ms": rag_response.took_ms,
            "chunks_used": rag_response.chunks_used,
            "model": rag_response.model,
        },
    )


@app.get("/documents/{document_id}", tags=["Documents"])
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get document metadata by ID.

    Returns full document metadata without chunk content.
    """
    logger.info("document_requested", document_id=str(document_id))

    search_service = SearchService(db_session=db, settings=settings)
    document = await search_service.get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return {
        "id": document.id,
        "title": document.title,
        "abstract": document.abstract,
        "authors": document.authors,
        "journal": document.journal,
        "publication_date": document.publication_date,
        "doi": document.doi,
        "pmcid": document.pmcid,
        "article_type": document.article_type,
        "processing_status": document.processing_status,
        "quality_score": document.quality_score,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


@app.get("/documents/{document_id}/chunks", tags=["Documents"])
async def get_document_chunks(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """
    Get chunks for a specific document.

    Returns paginated list of chunks with their content and metadata.
    """
    logger.info(
        "document_chunks_requested",
        document_id=str(document_id),
        limit=limit,
        offset=offset,
    )

    search_service = SearchService(db_session=db, settings=settings)
    chunks, total = await search_service.get_document_chunks(
        document_id=document_id,
        limit=limit,
        offset=offset,
    )

    return {
        "document_id": document_id,
        "chunks": [
            {
                "id": chunk.id,
                "content": chunk.content,
                "section_title": chunk.section_title,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/metrics", tags=["Observability"])
async def metrics() -> dict[str, Any]:
    """
    Prometheus-compatible metrics endpoint.

    Returns service metrics for monitoring.
    """
    # TODO: Implement actual metrics collection
    return {
        "search_requests_total": 0,
        "chat_requests_total": 0,
        "search_latency_seconds": {},
        "chat_latency_seconds": {},
        "cache_hit_rate": 0.0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.retrieval.src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
    )
