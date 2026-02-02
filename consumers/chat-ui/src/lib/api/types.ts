// Types matching Pydantic models from backend services

// Common types
export type UUID = string;

// Search types
export interface SearchFilters {
  date_from?: string;
  date_to?: string;
  journals?: string[];
  article_types?: string[];
}

export type SearchType = 'vector' | 'keyword' | 'hybrid';

export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  search_type?: SearchType;
  limit?: number;
  offset?: number;
  include_context?: boolean;
}

export interface ChunkMetadata {
  authors?: string[];
  journal?: string;
  publication_date?: string;
  doi?: string;
  pmcid?: string;
}

export interface ChunkContext {
  previous_chunk?: string;
  next_chunk?: string;
}

export interface SearchResult {
  chunk_id: UUID;
  document_id: UUID;
  title: string;
  content: string;
  section_title?: string;
  score: number;
  metadata: ChunkMetadata;
  context?: ChunkContext;
}

export interface QueryMetadata {
  took_ms: number;
  retrieval_strategy: string;
  filters_applied: Record<string, unknown>;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_metadata: QueryMetadata;
}

// Chat types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  query: string;
  filters?: SearchFilters;
  conversation_history?: ChatMessage[];
  max_chunks?: number;
}

export interface Citation {
  chunk_id: UUID;
  document_id: UUID;
  title: string;
  doi?: string;
  pmcid?: string;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  confidence_score: number;
  query_metadata: {
    took_ms: number;
    chunks_used: number;
    model: string;
  };
}

// Document types
export interface DocumentAuthor {
  name: string;
  affiliation?: string;
}

export interface Document {
  id: UUID;
  title: string;
  abstract?: string;
  authors: DocumentAuthor[];
  journal?: string;
  publication_date?: string;
  doi?: string;
  pmcid?: string;
  pmid?: string;
  article_type?: string;
  processing_status: ProcessingStatus;
  quality_score?: number;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  id: UUID;
  content: string;
  section_title?: string;
  chunk_index: number;
  token_count?: number;
}

export interface ChunksResponse {
  chunks: Chunk[];
  total: number;
}

// Ingestion types
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'retrying';

export interface IngestRequest {
  source_url?: string;
  s3_key?: string;
  document_type?: 'auto' | 'pubmed_xml' | 'pdf';
  priority?: number;
  metadata?: Record<string, unknown>;
}

export interface IngestResponse {
  job_id: string;
  document_id: string;
  status: string;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  document_id: string;
  status: ProcessingStatus;
  current_step?: string;
  completed_steps: number;
  total_steps: number;
  error_message?: string;
}

// Health types
export interface HealthResponse {
  status: string;
  version?: string;
  checks?: Record<string, { status: string; latency_ms?: number }>;
}

// API Error
export interface ApiError {
  detail: string;
  status?: number;
}
