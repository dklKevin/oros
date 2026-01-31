#!/usr/bin/env python3
"""
Test script for the ingestion pipeline.

Processes the downloaded test papers to verify the pipeline works correctly.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.shared.config import get_settings
from services.shared.logging import configure_logging, get_logger
from services.shared.database import DatabaseSession, init_db, close_db
from services.ingestion.src.processor import DocumentProcessor
from services.ingestion.src.parsers.pubmed_xml import PubMedXMLParser
from services.ingestion.src.chunking.strategies import SectionAwareChunker
from services.ingestion.src.embedder import get_embedder, PaddedLocalEmbedder

# Configure logging
settings = get_settings()
configure_logging(log_level="INFO", log_format="text")
logger = get_logger(__name__)


async def test_parser():
    """Test the PubMed XML parser with a sample file."""
    logger.info("=== Testing PubMed XML Parser ===")

    test_data_dir = project_root / "test-data" / "papers"

    if not test_data_dir.exists():
        logger.error(f"Test data directory not found: {test_data_dir}")
        return False

    # Get first XML file
    xml_files = list(test_data_dir.glob("*.xml"))
    if not xml_files:
        logger.error("No XML files found in test-data/papers")
        return False

    test_file = xml_files[0]
    logger.info(f"Testing with file: {test_file.name}")

    # Parse the file
    parser = PubMedXMLParser()

    with open(test_file, "rb") as f:
        content = f.read()

    if not parser.can_parse(content):
        logger.error("Parser cannot handle this file")
        return False

    try:
        doc = parser.parse(content)
        logger.info(f"  Title: {doc.title[:80]}...")
        logger.info(f"  Authors: {len(doc.authors)}")
        logger.info(f"  Journal: {doc.journal}")
        logger.info(f"  DOI: {doc.doi}")
        logger.info(f"  PMCID: {doc.pmcid}")
        logger.info(f"  Sections: {doc.section_count}")
        logger.info(f"  Has Abstract: {doc.has_abstract}")
        logger.info(f"  Word Count: {doc.word_count}")
        logger.info("Parser test PASSED")
        return doc
    except Exception as e:
        logger.exception(f"Parser test FAILED: {e}")
        return False


async def test_chunker(parsed_doc):
    """Test the chunking strategy."""
    logger.info("\n=== Testing Section-Aware Chunker ===")

    if not parsed_doc:
        logger.error("No parsed document to chunk")
        return False

    chunker = SectionAwareChunker(max_tokens=512, overlap_tokens=200)

    try:
        chunks = chunker.chunk(parsed_doc)
        logger.info(f"  Total chunks: {len(chunks)}")
        logger.info(f"  Total tokens: {sum(c.token_count for c in chunks)}")

        # Show first few chunks
        for i, chunk in enumerate(chunks[:3]):
            logger.info(f"  Chunk {i}: {chunk.section_title} ({chunk.token_count} tokens)")
            logger.info(f"    Preview: {chunk.content[:100]}...")

        logger.info("Chunker test PASSED")
        return chunks
    except Exception as e:
        logger.exception(f"Chunker test FAILED: {e}")
        return False


async def test_embedder(chunks):
    """Test the embedding generation."""
    logger.info("\n=== Testing Embedder ===")

    if not chunks:
        logger.error("No chunks to embed")
        return False

    # Use local embedder for testing
    embedder = get_embedder()

    logger.info(f"  Using model: {embedder.model_id}")
    logger.info(f"  Dimensions: {embedder.dimensions}")

    try:
        # Embed just a few chunks for testing
        test_chunks = chunks[:3]
        embeddings = embedder.embed_chunks(test_chunks)

        logger.info(f"  Generated {len(embeddings)} embeddings")
        logger.info(f"  Embedding shape: {len(embeddings[0])} dimensions")

        # Verify dimensions
        for i, emb in enumerate(embeddings):
            if len(emb) != embedder.dimensions:
                logger.error(f"  Chunk {i} has wrong dimensions: {len(emb)}")
                return False

        logger.info("Embedder test PASSED")
        return embeddings
    except Exception as e:
        logger.exception(f"Embedder test FAILED: {e}")
        return False


async def test_full_pipeline():
    """Test the full ingestion pipeline with database storage."""
    logger.info("\n=== Testing Full Pipeline ===")

    test_data_dir = project_root / "test-data" / "papers"
    xml_files = list(test_data_dir.glob("*.xml"))[:3]  # Test with 3 files

    if not xml_files:
        logger.error("No test files found")
        return False

    try:
        # Initialize database
        await init_db()

        results = []

        async with DatabaseSession() as db:
            # Create processor with local embedder (no S3 for testing)
            processor = DocumentProcessor(
                db_session=db,
                s3_client=None,  # Skip S3 for local testing
            )

            for xml_file in xml_files:
                logger.info(f"\nProcessing: {xml_file.name}")

                with open(xml_file, "rb") as f:
                    content = f.read()

                # Process without S3 (direct content)
                result = await processor.process_document(
                    content=content,
                    s3_key=f"test/{xml_file.name}",
                    metadata={"test": True, "source_file": str(xml_file)},
                )

                results.append(result)

                if result.success:
                    logger.info(f"  SUCCESS: {result.chunks_created} chunks created")
                else:
                    logger.error(f"  FAILED: {result.error_message}")

        # Summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"\nPipeline test: {successful}/{len(results)} documents processed successfully")

        return successful == len(results)

    except Exception as e:
        logger.exception(f"Pipeline test FAILED: {e}")
        return False
    finally:
        await close_db()


async def test_database_query():
    """Test querying the processed documents from the database."""
    logger.info("\n=== Testing Database Queries ===")

    try:
        await init_db()

        async with DatabaseSession() as db:
            from sqlalchemy import select, func
            from services.shared.models import Document, Chunk

            # Count documents
            result = await db.execute(select(func.count(Document.id)))
            doc_count = result.scalar()
            logger.info(f"  Documents in database: {doc_count}")

            # Count chunks
            result = await db.execute(select(func.count(Chunk.id)))
            chunk_count = result.scalar()
            logger.info(f"  Chunks in database: {chunk_count}")

            # Get a sample document
            result = await db.execute(
                select(Document).limit(1)
            )
            doc = result.scalar_one_or_none()

            if doc:
                logger.info(f"  Sample document: {doc.title[:60]}...")
                logger.info(f"    Status: {doc.processing_status}")
                logger.info(f"    Quality score: {doc.quality_score}")

                # Get its chunks
                result = await db.execute(
                    select(Chunk).where(Chunk.document_id == doc.id).limit(3)
                )
                chunks = result.scalars().all()
                logger.info(f"    Chunks: {len(chunks)}")

                for chunk in chunks:
                    has_embedding = chunk.embedding is not None
                    logger.info(f"      - {chunk.section_title}: {chunk.token_count} tokens, embedding={has_embedding}")

        logger.info("Database query test PASSED")
        return True

    except Exception as e:
        logger.exception(f"Database query test FAILED: {e}")
        return False
    finally:
        await close_db()


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Biomedical Knowledge Platform - Ingestion Pipeline Tests")
    logger.info("=" * 60)

    # Test 1: Parser
    parsed_doc = await test_parser()

    # Test 2: Chunker
    chunks = None
    if parsed_doc:
        chunks = await test_chunker(parsed_doc)

    # Test 3: Embedder
    if chunks:
        await test_embedder(chunks)

    # Test 4: Full pipeline (uncomment to test with database)
    logger.info("\n" + "=" * 60)
    logger.info("Testing full pipeline with database storage...")
    logger.info("=" * 60)

    pipeline_success = await test_full_pipeline()

    # Test 5: Database queries
    if pipeline_success:
        await test_database_query()

    logger.info("\n" + "=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
