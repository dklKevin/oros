# Biomedical Knowledge Platform

A production-ready platform for ingesting, processing, and querying biomedical scientific literature using semantic search and RAG (Retrieval-Augmented Generation).

## Overview

This platform enables researchers and healthcare professionals to:
- Ingest papers from PubMed, PDFs, and other sources
- Perform semantic search across the literature
- Get AI-powered answers with citations using RAG

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Biomedical Knowledge Platform                   │
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
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- AWS CLI (for deployment)
- Terraform 1.5+ (for infrastructure)

### Local Development

```bash
# Clone and setup
git clone <repository-url>
cd biomedical-knowledge-platform

# Install development dependencies
make setup-dev

# Copy environment template
cp .env.example .env

# Start local services (PostgreSQL, LocalStack)
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run database migrations
make db-migrate

# Seed with test data (optional)
python scripts/seed-data.py

# Run tests
make test
```

### Running Services Locally

```bash
# Run ingestion service
make run-ingestion

# Run retrieval service (in another terminal)
make run-retrieval
```

### API Endpoints

**Retrieval Service** (port 8000):
- `POST /search` - Semantic/hybrid search
- `POST /chat` - RAG-powered Q&A
- `GET /health` - Health check

**Ingestion Service** (port 8001):
- `POST /ingest` - Queue document for processing
- `GET /status/{job_id}` - Check processing status
- `GET /health` - Health check

### Example Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "CRISPR gene editing mechanisms",
    "search_type": "hybrid",
    "limit": 10
  }'
```

### Example Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main applications of CRISPR in cardiovascular disease treatment?",
    "max_chunks": 5
  }'
```

## Technology Stack

- **Language**: Python 3.11+
- **API Framework**: FastAPI
- **Database**: PostgreSQL 15 with pgvector
- **Vector Search**: HNSW index via pgvector
- **Embeddings**: AWS Bedrock Titan Embeddings
- **LLM**: AWS Bedrock Claude
- **Infrastructure**: AWS (ECS, RDS, S3, SQS)
- **IaC**: Terraform

## Project Structure

```
├── services/
│   ├── shared/           # Shared utilities (config, logging, models)
│   ├── ingestion/        # Document processing service
│   └── retrieval/        # Search and RAG service
├── infrastructure/
│   └── terraform/        # Infrastructure as code
├── scripts/              # Utility scripts
├── docs/                 # Documentation
└── test-data/            # Sample papers for testing
```

## Development

```bash
# Run linters
make lint

# Format code
make format

# Run tests with coverage
make test-cov
```

## Deployment

```bash
# Deploy to dev environment
make deploy-dev

# View Terraform plan
make tf-plan-dev
```

## Documentation

- [Architecture Design](docs/architecture/system-design.md)
- [API Documentation](docs/api/openapi.yaml)
- [Deployment Runbook](docs/runbooks/deployment.md)

## License

[Add your license here]
