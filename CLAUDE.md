# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Oros is a production-ready biomedical knowledge platform that ingests scientific literature (PubMed XML, PDFs), processes it for semantic search, and provides RAG-powered retrieval through a well-architected API system.

## Build and Run Commands

```bash
# Local Development
make setup              # Install dependencies, pre-commit hooks
docker-compose up       # Start all services (PostgreSQL, LocalStack, services)
docker-compose down     # Stop all services

# Testing
make test               # Run all tests
make test-ingestion     # Run ingestion service tests only
make test-retrieval     # Run retrieval service tests only
pytest services/ingestion/tests/test_parsers.py -v  # Run single test file

# Linting & Formatting
make lint               # Run ruff + mypy
make format             # Run black + ruff --fix

# Database
make db-migrate         # Run database migrations
make db-reset           # Reset database (WARNING: destroys data)

# Deployment
cd infrastructure/terraform/environments/dev && terraform apply
make deploy-dev         # Deploy to dev environment
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                              Oros                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   Ingest    │    │  Retrieval  │    │     API     │  Services   │
│  │   Service   │    │   Service   │    │   Gateway   │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│  ───────┴──────────────────┴──────────────────┴───────────────────  │
│                      Event Bus (SQS/EventBridge)                    │
│  ─────────────────────────────────────────────────────────────────  │
│         │                  │                  │                     │
│  ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐             │
│  │  Document   │    │   Vector    │    │  Metadata   │  Storage    │
│  │ Store (S3)  │    │DB (pgvector)│    │DB (Postgres)│             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Consumer Apps:  Chat UI  │  REST API  │  Batch Export             │
└─────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Core Infrastructure (AWS)
- **Compute**: ECS Fargate
- **Storage**: S3 (documents), RDS PostgreSQL 15+ with pgvector 0.5+ (HNSW indexes)
- **Messaging**: SQS + EventBridge
- **API**: API Gateway → ALB → ECS
- **Observability**: CloudWatch, X-Ray
- **IaC**: Terraform
- **Secrets**: AWS Secrets Manager

### Application Stack
- **Language**: Python 3.11+
- **API Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **Embeddings**: AWS Bedrock Titan Embeddings (1536 dimensions)
- **LLM**: AWS Bedrock Claude (Haiku for simple queries, Sonnet for synthesis)
- **Document Processing**: PyMuPDF (PDFs), lxml (XML)
- **Testing**: pytest, pytest-asyncio
- **Linting**: ruff, black, mypy

### Local Development
- Docker Compose with pgvector/pgvector:pg15 and LocalStack

## Key Architecture Decisions

### Embedding Model: Bedrock Titan Embeddings
- Managed service, no GPU infrastructure needed
- 1536 dimensions, good general performance
- Pay-per-use pricing
- Future option: PubMedBERT for domain-specific improvement

### Vector Index: HNSW (pgvector 0.5+)
- Better recall out-of-box than IVFFlat
- No tuning of `lists` parameter required
- Higher memory but worth the trade-off for accuracy

### Hybrid Search: Vector + BM25 with RRF
- Vector search via pgvector cosine similarity
- Keyword search via PostgreSQL full-text search with custom biomedical dictionary
- Reciprocal Rank Fusion for score combination
- Default weights: 0.7 vector, 0.3 keyword (configurable)

### Chunking Strategy: Section-Aware Hybrid
- Use paper section boundaries as primary break points
- Secondary chunking within long sections (>512 tokens)
- 200-token overlap between chunks
- Preserve metadata: section title, page number, chunk adjacency

## Database Schema (Critical Fields)

```sql
-- Documents table
documents (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    doi VARCHAR(255) UNIQUE,
    processing_status VARCHAR(20) DEFAULT 'pending',  -- pending/processing/completed/failed
    quality_score FLOAT,  -- 0-1 completeness metric
    retracted BOOLEAN DEFAULT FALSE,
    ...
)

-- Chunks table (with versioning)
chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(1536),  -- Bedrock Titan dimensions
    embedding_model_id VARCHAR(100),  -- e.g., 'amazon.titan-embed-text-v1'
    embedding_version INTEGER,  -- For tracking model updates
    ...
)

-- Use HNSW index for vector search
CREATE INDEX idx_chunks_embedding ON chunks
USING hnsw (embedding vector_cosine_ops);
```

## Code Quality Standards

- **Type hints**: All functions must have type hints
- **Docstrings**: Google-style for all public functions/classes
- **Testing**: Minimum 80% coverage
- **Linting**: Must pass ruff and mypy
- **Formatting**: Black with line length 100
- **Logging**: Structured JSON with correlation IDs

## RAG Implementation Guidelines

### Prompt Engineering for Biomedical
- Always include source DOI/PMCID in responses
- Handle contradictory research findings explicitly
- Implement confidence scoring based on supporting chunk count
- Support "I don't have enough information" responses

### Model Routing
- Claude Haiku: Simple lookups, factual queries
- Claude Sonnet: Complex synthesis, multi-paper analysis

### Context Management
- Retrieve 5-10 relevant chunks (~2000-4000 tokens)
- Include chunk adjacency context when relevant
- Strict token budgets per request

## Critical Implementation Notes

1. **Embedding Versioning**: Always store `embedding_model_id` and `embedding_version` with chunks to enable model upgrades without full reindex
2. **Document Quality**: Score documents on completeness (has_abstract, section_count, reference_count) and filter low-quality from retrieval
3. **Error Handling**: Expect ~10% PubMed XML parsing failures; validate and skip/flag problematic documents
4. **Deduplication**: Use DOI as primary key; implement fuzzy title matching for preprint/published duplicates
5. **Custom FTS Dictionary**: Add MeSH terms, drug names, gene symbols to PostgreSQL text search configuration

## Monitoring Metrics (Track from Day 1)

- Search latency p50/p95/p99
- Retrieval relevance score distribution
- Embedding generation throughput
- LLM token usage and costs per query
- Document processing success/failure rates
- Queue depth and DLQ message count

## Test Data

30 biomedical engineering papers available in `test-data/papers/` covering:
- CRISPR/Gene Editing (7 papers)
- Gene Therapy (8 papers)
- Tissue Engineering (6 papers)
- Medical Devices (5 papers)
- Biosensors (4 papers)

Manifest with metadata: `test-data/manifest.json`

## Implementation Status

### Document Parsers ✅
| Parser | Status | Coverage | Tests |
|--------|--------|----------|-------|
| PubMed XML Parser | ✅ Complete | 60% | 13 tests |
| PDF Parser | ✅ Complete | 83% | 25 tests |

**PDF Parser Features** (`services/ingestion/src/parsers/pdf.py`):
- Extracts: title, abstract, sections, authors, DOI, PMCID, PMID, references, keywords
- Section detection for biomedical papers (Introduction, Methods, Results, Discussion)
- Metadata extraction from PDF properties
- Author parsing from both metadata and text content
- Reference extraction with DOI/year detection
- Robust error handling with `ParseError`

### Ingestion Service ✅
| Component | Status | Tests |
|-----------|--------|-------|
| API Endpoints | ✅ Complete | 7 tests |
| Document Processor | ✅ Complete | 9 tests |
| Chunking Strategies | ✅ Complete | 7 tests |
| Embedder | ✅ Complete | 11 tests |
| Parsers (Base + XML + PDF) | ✅ Complete | 56 tests |

**Total Ingestion Tests**: 90 passing

### Retrieval Service ✅
| Component | Status | Description |
|-----------|--------|-------------|
| Search Service | ✅ Complete | Vector, keyword, and hybrid search |
| RAG Service | ✅ Complete | AWS Bedrock Claude integration |
| API Endpoints | ✅ Complete | /search, /chat, /documents |

### Security Hardening ✅
- Production credential validation (blocks default passwords)
- CORS configuration with explicit allowed origins
- Path traversal prevention with whitelist validation
- Query length validation (max 10,000 chars)
- In-memory rate limiting with sliding window
- Generic error messages (no internal details exposed)

### Infrastructure
| Component | Status |
|-----------|--------|
| PostgreSQL + pgvector | ✅ Docker Compose ready |
| LocalStack (S3) | ✅ Docker Compose ready |
| Database Schema | ✅ init-db.sql complete |
| E2E Test Infrastructure | ✅ 25 tests passing |

### Pending Development
| Component | Priority | Notes |
|-----------|----------|-------|
| SQS Worker | High | Queue processing for async ingestion |
| API Gateway | Medium | Unified API entry point |
| Chat UI | Low | Consumer application |
| CLI Tool | Low | Consumer application |
| Custom FTS Dictionary | Low | MeSH terms, drug names |
