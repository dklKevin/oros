-- =============================================================================
-- Oros - Database Initialization
-- =============================================================================
-- This script runs when PostgreSQL container starts for the first time

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Custom Text Search Configuration for Biomedical Terms
-- =============================================================================
-- Create a custom text search configuration based on English
CREATE TEXT SEARCH CONFIGURATION biomedical (COPY = english);

-- Note: In production, you would add a custom dictionary with MeSH terms,
-- drug names, and gene symbols. For now, we use the default English config.

-- =============================================================================
-- Documents Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Core metadata
    title TEXT NOT NULL,
    abstract TEXT,
    authors JSONB DEFAULT '[]'::jsonb,
    journal VARCHAR(500),
    publication_date DATE,

    -- Identifiers
    doi VARCHAR(255) UNIQUE,
    pmcid VARCHAR(50) UNIQUE,
    pmid VARCHAR(50),

    -- Classification
    mesh_terms JSONB DEFAULT '[]'::jsonb,
    keywords JSONB DEFAULT '[]'::jsonb,
    article_type VARCHAR(100),

    -- Source and storage
    source_url TEXT,
    s3_key TEXT NOT NULL,
    s3_bucket VARCHAR(255),

    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'retrying')),
    processing_error TEXT,
    processing_attempts INTEGER DEFAULT 0,

    -- Quality metrics
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),
    has_abstract BOOLEAN DEFAULT FALSE,
    has_full_text BOOLEAN DEFAULT FALSE,
    section_count INTEGER DEFAULT 0,
    reference_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,

    -- Flags
    retracted BOOLEAN DEFAULT FALSE,
    retraction_date DATE,
    retraction_reason TEXT,

    -- Additional metadata (named extra_metadata to avoid SQLAlchemy reserved name)
    extra_metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- =============================================================================
-- Chunks Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    content_hash VARCHAR(64), -- SHA-256 for deduplication

    -- Position and structure
    section_title VARCHAR(500),
    section_type VARCHAR(100), -- introduction, methods, results, discussion, etc.
    chunk_index INTEGER NOT NULL, -- Order within document
    page_number INTEGER,

    -- Token information
    token_count INTEGER,

    -- Embedding with versioning (1536 dimensions for Bedrock Titan)
    embedding vector(1536),
    embedding_model_id VARCHAR(100), -- e.g., 'amazon.titan-embed-text-v1'
    embedding_version INTEGER DEFAULT 1,
    embedding_created_at TIMESTAMP WITH TIME ZONE,

    -- Chunk relationships
    previous_chunk_id UUID REFERENCES chunks(id) ON DELETE SET NULL,
    next_chunk_id UUID REFERENCES chunks(id) ON DELETE SET NULL,

    -- Additional metadata (named extra_metadata to avoid SQLAlchemy reserved name)
    extra_metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Processing Jobs Table (for tracking async ingestion)
-- =============================================================================
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    -- Job details
    job_type VARCHAR(50) NOT NULL, -- 'ingestion', 'embedding', 'reindex'
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,

    -- Progress tracking
    total_steps INTEGER,
    completed_steps INTEGER DEFAULT 0,
    current_step VARCHAR(255),

    -- Error handling
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- SQS integration
    sqs_message_id VARCHAR(255),
    sqs_receipt_handle TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Additional metadata (named extra_metadata to avoid SQLAlchemy reserved name)
    extra_metadata JSONB DEFAULT '{}'::jsonb
);

-- =============================================================================
-- Search History Table (for analytics)
-- =============================================================================
CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Query details
    query_text TEXT NOT NULL,
    query_embedding vector(1536),
    search_type VARCHAR(20) NOT NULL, -- 'vector', 'keyword', 'hybrid'

    -- Filters applied
    filters JSONB DEFAULT '{}'::jsonb,

    -- Results
    result_count INTEGER,
    result_ids UUID[],

    -- Performance
    latency_ms INTEGER,

    -- User context (optional, for future use)
    user_id VARCHAR(255),
    session_id VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_doi ON documents(doi);
CREATE INDEX IF NOT EXISTS idx_documents_pmcid ON documents(pmcid);
CREATE INDEX IF NOT EXISTS idx_documents_publication_date ON documents(publication_date);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_journal ON documents(journal);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

-- Full-text search indexes for documents
CREATE INDEX IF NOT EXISTS idx_documents_title_fts
    ON documents USING gin(to_tsvector('biomedical', title));
CREATE INDEX IF NOT EXISTS idx_documents_abstract_fts
    ON documents USING gin(to_tsvector('biomedical', COALESCE(abstract, '')));

-- Trigram indexes for fuzzy matching
CREATE INDEX IF NOT EXISTS idx_documents_title_trgm
    ON documents USING gin(title gin_trgm_ops);

-- Chunks indexes
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_section_type ON chunks(section_type);
CREATE INDEX IF NOT EXISTS idx_chunks_content_hash ON chunks(content_hash);

-- HNSW vector index for semantic search (pgvector 0.5+)
-- HNSW provides better recall than IVFFlat without parameter tuning
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search index for chunks
CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
    ON chunks USING gin(to_tsvector('biomedical', content));

-- Processing jobs indexes
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at ON processing_jobs(created_at);

-- Search history indexes
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);

-- =============================================================================
-- Functions
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to calculate document quality score
CREATE OR REPLACE FUNCTION calculate_quality_score(doc documents)
RETURNS FLOAT AS $$
DECLARE
    score FLOAT := 0.0;
BEGIN
    -- Has abstract: 0.3 points
    IF doc.has_abstract THEN
        score := score + 0.3;
    END IF;

    -- Has full text: 0.3 points
    IF doc.has_full_text THEN
        score := score + 0.3;
    END IF;

    -- Section count: up to 0.2 points (max at 5+ sections)
    score := score + LEAST(doc.section_count / 5.0, 1.0) * 0.2;

    -- Reference count: up to 0.2 points (max at 20+ references)
    score := score + LEAST(doc.reference_count / 20.0, 1.0) * 0.2;

    RETURN score;
END;
$$ LANGUAGE plpgsql;

-- Function for hybrid search (vector + keyword with RRF)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1536),
    query_text TEXT,
    match_count INTEGER DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    filter_journals TEXT[] DEFAULT NULL,
    filter_date_from DATE DEFAULT NULL,
    filter_date_to DATE DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    section_title VARCHAR(500),
    vector_rank INTEGER,
    keyword_rank INTEGER,
    rrf_score FLOAT,
    vector_similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            c.id,
            c.document_id,
            c.content,
            c.section_title,
            1 - (c.embedding <=> query_embedding) as similarity,
            ROW_NUMBER() OVER (ORDER BY c.embedding <=> query_embedding) as rank
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
            AND d.processing_status = 'completed'
            AND (filter_journals IS NULL OR d.journal = ANY(filter_journals))
            AND (filter_date_from IS NULL OR d.publication_date >= filter_date_from)
            AND (filter_date_to IS NULL OR d.publication_date <= filter_date_to)
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    keyword_results AS (
        SELECT
            c.id,
            c.document_id,
            c.content,
            c.section_title,
            ts_rank(to_tsvector('biomedical', c.content), plainto_tsquery('biomedical', query_text)) as rank_score,
            ROW_NUMBER() OVER (ORDER BY ts_rank(to_tsvector('biomedical', c.content), plainto_tsquery('biomedical', query_text)) DESC) as rank
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE to_tsvector('biomedical', c.content) @@ plainto_tsquery('biomedical', query_text)
            AND d.processing_status = 'completed'
            AND (filter_journals IS NULL OR d.journal = ANY(filter_journals))
            AND (filter_date_from IS NULL OR d.publication_date >= filter_date_from)
            AND (filter_date_to IS NULL OR d.publication_date <= filter_date_to)
        ORDER BY rank_score DESC
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT
            COALESCE(v.id, k.id) as chunk_id,
            COALESCE(v.document_id, k.document_id) as document_id,
            COALESCE(v.content, k.content) as content,
            COALESCE(v.section_title, k.section_title) as section_title,
            COALESCE(v.rank, 1000)::INTEGER as vector_rank,
            COALESCE(k.rank, 1000)::INTEGER as keyword_rank,
            v.similarity as vector_similarity,
            -- RRF formula: 1/(k + rank) where k=60 is standard
            (vector_weight * (1.0 / (60 + COALESCE(v.rank, 1000))) +
             keyword_weight * (1.0 / (60 + COALESCE(k.rank, 1000)))) as rrf_score
        FROM vector_results v
        FULL OUTER JOIN keyword_results k ON v.id = k.id
    )
    SELECT
        combined.chunk_id,
        combined.document_id,
        combined.content,
        combined.section_title,
        combined.vector_rank,
        combined.keyword_rank,
        combined.rrf_score,
        combined.vector_similarity
    FROM combined
    ORDER BY combined.rrf_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Triggers
-- =============================================================================

-- Auto-update updated_at for documents
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at for chunks
DROP TRIGGER IF EXISTS update_chunks_updated_at ON chunks;
CREATE TRIGGER update_chunks_updated_at
    BEFORE UPDATE ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Initial Data / Configuration
-- =============================================================================

-- Create a view for document statistics
CREATE OR REPLACE VIEW document_stats AS
SELECT
    processing_status,
    COUNT(*) as count,
    AVG(quality_score) as avg_quality_score,
    AVG(section_count) as avg_section_count,
    AVG(word_count) as avg_word_count
FROM documents
GROUP BY processing_status;

-- Create a view for chunk statistics
CREATE OR REPLACE VIEW chunk_stats AS
SELECT
    d.processing_status,
    COUNT(c.id) as total_chunks,
    AVG(c.token_count) as avg_token_count,
    COUNT(CASE WHEN c.embedding IS NOT NULL THEN 1 END) as chunks_with_embeddings
FROM documents d
LEFT JOIN chunks c ON d.id = c.document_id
GROUP BY d.processing_status;

-- =============================================================================
-- Grants (for application user)
-- =============================================================================
-- Note: In production, create a separate application user with limited privileges

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO biomedical;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO biomedical;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO biomedical;
