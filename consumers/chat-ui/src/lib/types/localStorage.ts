import type { SearchFilters, SearchType } from '@/lib/api/types';

/**
 * Search history entry stored in localStorage
 */
export interface SearchHistoryItem {
  id: string;
  query: string;
  filters?: SearchFilters;
  searchType?: SearchType;
  timestamp: number;
}

/**
 * Bookmarked document stored in localStorage
 */
export interface BookmarkedDocument {
  document_id: string;
  title: string;
  doi?: string;
  authors?: string[];
  bookmarked_at: number;
}
