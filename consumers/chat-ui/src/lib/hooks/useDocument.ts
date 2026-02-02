'use client';

import { useQuery } from '@tanstack/react-query';
import { getDocument, getDocumentChunks } from '@/lib/api/retrieval';
import type { Document, ChunksResponse } from '@/lib/api/types';

export function useDocument(documentId: string | undefined) {
  return useQuery<Document>({
    queryKey: ['document', documentId],
    queryFn: () => getDocument(documentId!),
    enabled: !!documentId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useDocumentChunks(
  documentId: string | undefined,
  options?: { limit?: number; offset?: number }
) {
  return useQuery<ChunksResponse>({
    queryKey: ['document-chunks', documentId, options],
    queryFn: () => getDocumentChunks(documentId!, options),
    enabled: !!documentId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
