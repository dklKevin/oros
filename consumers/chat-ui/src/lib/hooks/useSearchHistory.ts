'use client';

import { useCallback } from 'react';
import { useLocalStorage } from './useLocalStorage';
import type { SearchHistoryItem } from '@/lib/types/localStorage';
import type { SearchFilters, SearchType } from '@/lib/api/types';
import { SEARCH_HISTORY_KEY, SEARCH_HISTORY_MAX_ITEMS } from '@/lib/utils/constants';

/**
 * Hook for managing search history in localStorage.
 * Stores up to SEARCH_HISTORY_MAX_ITEMS most recent searches.
 */
export function useSearchHistory() {
  const [history, setHistory, clearHistory] = useLocalStorage<SearchHistoryItem[]>(
    SEARCH_HISTORY_KEY,
    []
  );

  const addSearch = useCallback(
    (query: string, filters?: SearchFilters, searchType?: SearchType) => {
      if (!query.trim()) return;

      const newItem: SearchHistoryItem = {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        query: query.trim(),
        filters,
        searchType,
        timestamp: Date.now(),
      };

      setHistory((prev) => {
        // Remove duplicate queries (case-insensitive)
        const filtered = prev.filter(
          (item) => item.query.toLowerCase() !== query.trim().toLowerCase()
        );
        // Add new item at the beginning, limit to max items
        return [newItem, ...filtered].slice(0, SEARCH_HISTORY_MAX_ITEMS);
      });
    },
    [setHistory]
  );

  const removeSearch = useCallback(
    (id: string) => {
      setHistory((prev) => prev.filter((item) => item.id !== id));
    },
    [setHistory]
  );

  return {
    history,
    addSearch,
    removeSearch,
    clearHistory,
  };
}
