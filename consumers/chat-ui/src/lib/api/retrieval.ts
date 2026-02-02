import { retrievalApi } from './client';
import type {
  SearchRequest,
  SearchResponse,
  ChatRequest,
  ChatResponse,
  Document,
  ChunksResponse,
  HealthResponse,
} from './types';

export async function search(request: SearchRequest): Promise<SearchResponse> {
  return retrievalApi.post<SearchResponse>('/search', request);
}

export async function chat(request: ChatRequest): Promise<ChatResponse> {
  return retrievalApi.post<ChatResponse>('/chat', request);
}

export async function getDocument(documentId: string): Promise<Document> {
  return retrievalApi.get<Document>(`/documents/${documentId}`);
}

export async function getDocumentChunks(
  documentId: string,
  options?: { limit?: number; offset?: number }
): Promise<ChunksResponse> {
  return retrievalApi.get<ChunksResponse>(`/documents/${documentId}/chunks`, {
    params: options,
  });
}

export async function getRetrievalHealth(): Promise<HealthResponse> {
  return retrievalApi.get<HealthResponse>('/health');
}
