"""
Ingestion Service - FastAPI Application Entry Point.

Provides endpoints for document ingestion and processing status.
"""

from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import get_settings
from services.shared.database import (
    close_db,
    get_db,
    health_check as db_health_check,
    init_db,
)
from services.shared.logging import configure_logging, get_logger, LoggingMiddleware
from services.shared.models import Document, ProcessingJob, ProcessingStatus, JobType

settings = get_settings()
configure_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    service_name="ingestion-service",
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("starting_ingestion_service", environment=settings.environment)
    await init_db()
    yield
    # Shutdown
    logger.info("stopping_ingestion_service")
    await close_db()


app = FastAPI(
    title="Biomedical Knowledge Platform - Ingestion Service",
    description="Document ingestion, parsing, and embedding generation",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(LoggingMiddleware, service_name="ingestion-service")

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
class IngestRequest(BaseModel):
    """Request model for document ingestion."""

    source_url: str | None = Field(None, description="URL to fetch document from")
    s3_key: str | None = Field(None, description="S3 key if document already uploaded")
    document_type: str = Field("auto", description="Document type (auto, pubmed_xml, pdf)")
    priority: int = Field(0, ge=0, le=10, description="Processing priority")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class IngestResponse(BaseModel):
    """Response model for document ingestion."""

    job_id: str
    document_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    document_id: str | None
    status: str
    current_step: str | None
    completed_steps: int
    total_steps: int | None
    error_message: str | None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    service: str
    database: dict[str, Any]


class IngestLocalRequest(BaseModel):
    """Request model for local file ingestion (testing)."""

    file_path: str = Field(..., description="Path to local file")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class IngestLocalResponse(BaseModel):
    """Response model for local file ingestion."""

    document_id: str
    status: str
    chunks_created: int
    message: str


# =============================================================================
# Background Processing
# =============================================================================
async def process_document_background(
    document_id: UUID,
    s3_key: str | None,
    source_url: str | None,
    job_id: UUID,
) -> None:
    """Background task to process a document."""
    from services.shared.database import DatabaseSession
    from services.shared.storage import get_s3_client
    from services.ingestion.src.processor import DocumentProcessor

    try:
        async with DatabaseSession() as db:
            # Update job status to processing
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = ProcessingStatus.PROCESSING
                job.current_step = "initializing"
                await db.commit()

            # Create processor and process document
            processor = DocumentProcessor(db_session=db)
            processing_result = await processor.process_document(
                document_id=document_id,
                s3_key=s3_key,
                source_url=source_url,
            )

            # Update job status based on result
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                if processing_result.success:
                    job.status = ProcessingStatus.COMPLETED
                    job.current_step = "completed"
                    job.completed_steps = 5
                    job.total_steps = 5
                else:
                    job.status = ProcessingStatus.FAILED
                    job.error_message = processing_result.error_message
                await db.commit()

            logger.info(
                "background_processing_complete",
                document_id=str(document_id),
                success=processing_result.success,
                chunks_created=processing_result.chunks_created,
            )

    except Exception as e:
        logger.exception("background_processing_error", document_id=str(document_id), error=str(e))


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
        service="ingestion",
        database=db_status,
    )


@app.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Ingestion"],
)
async def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """
    Queue a document for ingestion.

    Accepts either a source URL or S3 key for an already-uploaded document.
    Returns a job ID for tracking processing status.
    """
    if not request.source_url and not request.s3_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either source_url or s3_key must be provided",
        )

    # Generate IDs
    document_id = uuid4()
    job_id = uuid4()

    # Create document record (minimal, will be updated during processing)
    document = Document(
        id=document_id,
        title="Pending Processing",
        s3_key=request.s3_key or f"documents/{document_id}.xml",
        source_url=request.source_url,
        processing_status=ProcessingStatus.PENDING,
        extra_metadata=request.metadata,
    )
    db.add(document)

    # Create processing job
    job = ProcessingJob(
        id=job_id,
        document_id=document_id,
        job_type=JobType.INGESTION,
        status=ProcessingStatus.PENDING,
        priority=request.priority,
        total_steps=5,  # fetch, parse, chunk, embed, store
        completed_steps=0,
        current_step="queued",
    )
    db.add(job)

    await db.flush()

    # Queue background processing
    background_tasks.add_task(
        process_document_background,
        document_id=document_id,
        s3_key=request.s3_key,
        source_url=request.source_url,
        job_id=job_id,
    )

    logger.info(
        "document_ingestion_queued",
        document_id=str(document_id),
        job_id=str(job_id),
        source_url=request.source_url,
        s3_key=request.s3_key,
        document_type=request.document_type,
    )

    return IngestResponse(
        job_id=str(job_id),
        document_id=str(document_id),
        status="queued",
        message="Document queued for processing",
    )


@app.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    tags=["Ingestion"],
)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """
    Get the status of a processing job.

    Returns current progress and any error information.
    """
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_uuid)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    logger.info("job_status_requested", job_id=job_id, status=job.status)

    return JobStatusResponse(
        job_id=str(job.id),
        document_id=str(job.document_id) if job.document_id else None,
        status=job.status.value if isinstance(job.status, ProcessingStatus) else job.status,
        current_step=job.current_step,
        completed_steps=job.completed_steps,
        total_steps=job.total_steps,
        error_message=job.error_message,
    )


# Allowed base paths for local file ingestion (security: prevent path traversal)
ALLOWED_LOCAL_PATHS = [
    "/data/uploads",
    "/tmp/ingestion",
    "./test-data",
    "test-data",
]


def validate_file_path(file_path: str) -> str:
    """
    Validate file path to prevent path traversal attacks.

    Args:
        file_path: The requested file path

    Returns:
        Resolved absolute path if valid

    Raises:
        HTTPException: If path is not allowed
    """
    import os

    # Resolve to absolute path and normalize
    abs_path = os.path.abspath(os.path.normpath(file_path))

    # Check for path traversal attempts
    if ".." in file_path:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path traversal not allowed",
        )

    # Verify path is within allowed directories
    allowed = False
    for base in ALLOWED_LOCAL_PATHS:
        abs_base = os.path.abspath(os.path.normpath(base))
        if abs_path.startswith(abs_base):
            allowed = True
            break

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="File path not in allowed directories. Allowed: /data/uploads, /tmp/ingestion, ./test-data",
        )

    return abs_path


@app.post(
    "/ingest/local",
    response_model=IngestLocalResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Ingestion"],
)
async def ingest_local_file(
    request: IngestLocalRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestLocalResponse:
    """
    Process a local file directly (for testing/development).

    This endpoint processes the file synchronously and returns the result.
    Use /ingest for production async processing.

    Note: Only files in allowed directories can be processed for security.
    """
    import os

    # Security: Validate path to prevent traversal attacks
    validated_path = validate_file_path(request.file_path)

    if not os.path.exists(validated_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {request.file_path}",
        )

    from services.ingestion.src.processor import DocumentProcessor

    processor = DocumentProcessor(db_session=db)
    result = await processor.process_local_file(
        file_path=validated_path,
        metadata=request.metadata,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.error_message or "Processing failed",
        )

    logger.info(
        "local_file_processed",
        file_path=validated_path,
        document_id=str(result.document_id),
        chunks_created=result.chunks_created,
    )

    return IngestLocalResponse(
        document_id=str(result.document_id),
        status="processing",
        chunks_created=result.chunks_created,
        message=f"Document processed successfully with {result.chunks_created} chunks",
    )


@app.get("/metrics", tags=["Observability"])
async def metrics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Prometheus-compatible metrics endpoint.

    Returns service metrics for monitoring.
    """
    from sqlalchemy import func

    # Get document counts by status
    result = await db.execute(
        select(
            Document.processing_status,
            func.count(Document.id).label("count"),
        ).group_by(Document.processing_status)
    )
    status_counts = {row.processing_status: row.count for row in result}

    # Get total chunks
    from services.shared.models import Chunk
    chunk_result = await db.execute(select(func.count(Chunk.id)))
    total_chunks = chunk_result.scalar() or 0

    return {
        "documents_processed_total": status_counts.get("completed", 0),
        "documents_failed_total": status_counts.get("failed", 0),
        "documents_pending_total": status_counts.get("pending", 0),
        "total_chunks": total_chunks,
        "processing_duration_seconds": {},
        "queue_depth": status_counts.get("pending", 0),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.ingestion.src.main:app",
        host=settings.api_host,
        port=8001,
        reload=settings.is_development,
    )
