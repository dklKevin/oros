"""
Document processing pipeline.

Orchestrates the full ingestion flow:
1. Fetch/load document
2. Parse content
3. Chunk into sections
4. Generate embeddings
5. Store in database and S3
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import Settings, get_settings
from services.shared.logging import get_logger
from services.shared.models import Chunk as ChunkModel, Document, ProcessingStatus
from services.shared.storage import S3Client, get_s3_client

from services.ingestion.src.parsers.base import ParsedDocument, ParseError
from services.ingestion.src.parsers.pubmed_xml import PubMedXMLParser
from services.ingestion.src.chunking.strategies import Chunk, SectionAwareChunker
from services.ingestion.src.embedder import Embedder, get_embedder

logger = get_logger(__name__)


class ProcessingResult:
    """Result of document processing."""

    def __init__(
        self,
        document_id: UUID,
        success: bool,
        chunks_created: int = 0,
        error_message: str | None = None,
        error_details: dict[str, Any] | None = None,
    ):
        self.document_id = document_id
        self.success = success
        self.chunks_created = chunks_created
        self.error_message = error_message
        self.error_details = error_details or {}


class DocumentProcessor:
    """
    Main document processing pipeline.

    Handles the complete flow from raw document to indexed chunks.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        s3_client: S3Client | None = None,
        embedder: Embedder | None = None,
        settings: Settings | None = None,
    ):
        self.db = db_session
        self.settings = settings or get_settings()
        self.s3_client = s3_client or get_s3_client(self.settings)
        self.embedder = embedder or get_embedder(self.settings)

        # Initialize parsers
        self.parsers = [
            PubMedXMLParser(),
            # Add more parsers here (PDF, etc.)
        ]

        # Initialize chunker
        self.chunker = SectionAwareChunker(
            max_tokens=self.settings.chunk_max_tokens,
            overlap_tokens=self.settings.chunk_overlap_tokens,
        )

    async def process_document(
        self,
        document_id: UUID | None = None,
        source_url: str | None = None,
        s3_key: str | None = None,
        content: bytes | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProcessingResult:
        """
        Process a document through the full pipeline.

        Args:
            document_id: Existing document ID (for reprocessing)
            source_url: URL to fetch document from
            s3_key: S3 key if document already uploaded
            content: Raw document content (if already loaded)
            metadata: Additional metadata to store

        Returns:
            ProcessingResult with status and details
        """
        doc_id = document_id or uuid4()
        metadata = metadata or {}

        try:
            logger.info(
                "processing_started",
                document_id=str(doc_id),
                source_url=source_url,
                s3_key=s3_key,
            )

            # Step 1: Get document content
            if content is None:
                if s3_key:
                    content = await self.s3_client.download_document(s3_key)
                elif source_url:
                    content = await self._fetch_from_url(source_url)
                else:
                    raise ValueError("No content source provided")

            # Step 2: Parse document
            parsed_doc = self._parse_document(content)

            # Step 3: Create/update document record
            document = await self._create_document_record(
                doc_id=doc_id,
                parsed_doc=parsed_doc,
                s3_key=s3_key or f"documents/{doc_id}.xml",
                source_url=source_url,
                metadata=metadata,
            )

            # Step 4: Upload to S3 if not already there
            if not s3_key:
                s3_key = f"documents/{doc_id}.xml"
                await self.s3_client.upload_document(
                    content=content,
                    key=s3_key,
                    content_type="application/xml",
                    metadata={"document_id": str(doc_id)},
                )
                document.s3_key = s3_key

            # Step 5: Chunk document
            chunks = self.chunker.chunk(parsed_doc)

            # Step 6: Generate embeddings
            embeddings = self.embedder.embed_chunks(chunks)

            # Step 7: Store chunks with embeddings
            await self._store_chunks(
                document_id=document.id,
                chunks=chunks,
                embeddings=embeddings,
            )

            # Step 8: Update document status
            document.processing_status = ProcessingStatus.COMPLETED
            document.processed_at = datetime.now(timezone.utc)
            document.quality_score = document.calculate_quality_score()

            await self.db.commit()

            logger.info(
                "processing_completed",
                document_id=str(doc_id),
                chunks_created=len(chunks),
                quality_score=document.quality_score,
            )

            return ProcessingResult(
                document_id=doc_id,
                success=True,
                chunks_created=len(chunks),
            )

        except ParseError as e:
            logger.error(
                "processing_parse_error",
                document_id=str(doc_id),
                error=str(e),
            )
            await self._mark_failed(doc_id, str(e), e.details)
            return ProcessingResult(
                document_id=doc_id,
                success=False,
                error_message=str(e),
                error_details=e.details,
            )

        except Exception as e:
            logger.exception(
                "processing_error",
                document_id=str(doc_id),
                error=str(e),
            )
            await self._mark_failed(doc_id, str(e))
            return ProcessingResult(
                document_id=doc_id,
                success=False,
                error_message=str(e),
            )

    async def process_local_file(
        self,
        file_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProcessingResult:
        """
        Process a local file.

        Convenience method for processing files from the filesystem.

        Args:
            file_path: Path to the file
            metadata: Additional metadata

        Returns:
            ProcessingResult
        """
        with open(file_path, "rb") as f:
            content = f.read()

        # Extract filename for S3 key
        import os
        filename = os.path.basename(file_path)

        return await self.process_document(
            content=content,
            s3_key=f"documents/{filename}",
            metadata=metadata or {"source_file": file_path},
        )

    def _parse_document(self, content: bytes) -> ParsedDocument:
        """Parse document content using appropriate parser."""
        for parser in self.parsers:
            if parser.can_parse(content):
                return parser.parse(content)

        raise ParseError(
            "No suitable parser found for document",
            {"content_preview": content[:200].decode("utf-8", errors="ignore")},
        )

    async def _fetch_from_url(self, url: str) -> bytes:
        """Fetch document content from URL."""
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def _create_document_record(
        self,
        doc_id: UUID,
        parsed_doc: ParsedDocument,
        s3_key: str,
        source_url: str | None,
        metadata: dict[str, Any],
    ) -> Document:
        """Create or update document record in database."""
        # Check if document exists
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        document = result.scalar_one_or_none()

        if document is None:
            # Create new document
            document = Document(
                id=doc_id,
                title=parsed_doc.title,
                abstract=parsed_doc.abstract,
                authors=[
                    {
                        "given_names": a.given_names,
                        "surname": a.surname,
                        "email": a.email,
                        "affiliations": a.affiliations,
                        "orcid": a.orcid,
                    }
                    for a in parsed_doc.authors
                ],
                journal=parsed_doc.journal,
                publication_date=parsed_doc.publication_date,
                doi=parsed_doc.doi,
                pmcid=parsed_doc.pmcid,
                pmid=parsed_doc.pmid,
                mesh_terms=parsed_doc.mesh_terms,
                keywords=parsed_doc.keywords,
                article_type=parsed_doc.article_type,
                source_url=source_url,
                s3_key=s3_key,
                s3_bucket=self.settings.s3_bucket_raw_documents,
                processing_status=ProcessingStatus.PROCESSING,
                has_abstract=parsed_doc.has_abstract,
                has_full_text=parsed_doc.has_full_text,
                section_count=parsed_doc.section_count,
                reference_count=len(parsed_doc.references),
                word_count=parsed_doc.word_count,
                extra_metadata=metadata,
            )
            self.db.add(document)
        else:
            # Update existing document
            document.title = parsed_doc.title
            document.abstract = parsed_doc.abstract
            document.processing_status = ProcessingStatus.PROCESSING
            document.processing_attempts += 1

        await self.db.flush()
        return document

    async def _store_chunks(
        self,
        document_id: UUID,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Store chunks with embeddings in database."""
        # Delete existing chunks for this document (for reprocessing)
        from sqlalchemy import delete
        await self.db.execute(
            delete(ChunkModel).where(ChunkModel.document_id == document_id)
        )

        # Create new chunk records
        chunk_models: list[ChunkModel] = []
        previous_chunk_id: UUID | None = None

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_model = ChunkModel(
                id=uuid4(),
                document_id=document_id,
                content=chunk.content,
                content_hash=chunk.content_hash,
                section_title=chunk.section_title,
                section_type=chunk.section_type,
                chunk_index=chunk.chunk_index,
                token_count=chunk.token_count,
                embedding=embedding,
                embedding_model_id=self.embedder.model_id,
                embedding_version=1,
                embedding_created_at=datetime.now(timezone.utc),
                previous_chunk_id=previous_chunk_id,
                extra_metadata=chunk.metadata,
            )
            self.db.add(chunk_model)
            chunk_models.append(chunk_model)
            previous_chunk_id = chunk_model.id

        # Update next_chunk_id references
        await self.db.flush()
        for i, chunk_model in enumerate(chunk_models[:-1]):
            chunk_model.next_chunk_id = chunk_models[i + 1].id

    async def _mark_failed(
        self,
        document_id: UUID,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ) -> None:
        """Mark document as failed."""
        try:
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if document:
                document.processing_status = ProcessingStatus.FAILED
                document.processing_error = error_message
                document.processing_attempts += 1
                await self.db.commit()
        except Exception as e:
            logger.error("failed_to_mark_failed", error=str(e))
            await self.db.rollback()
