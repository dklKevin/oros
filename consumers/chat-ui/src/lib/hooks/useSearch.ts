'use client';

import { useQuery } from '@tanstack/react-query';
import { search } from '@/lib/api/retrieval';
import type { SearchRequest, SearchResponse } from '@/lib/api/types';

export function useSearch(request: SearchRequest | null, enabled = true) {
  return useQuery<SearchResponse>({
    queryKey: ['search', request],
    queryFn: () => search(request!),
    enabled: enabled && !!request?.query,
    staleTime: 1000 * 60, // 1 minute
  });
}
