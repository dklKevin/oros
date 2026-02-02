'use client';

import { useState, useMemo, useCallback } from 'react';
import { SearchBar, SearchFilters, SearchResultCard, Pagination } from '@/components/search';
import { Spinner, SkeletonCard } from '@/components/ui';
import { useSearch, useDebounce, useSearchHistory } from '@/lib/hooks';
import type { SearchFilters as SearchFiltersType, SearchType } from '@/lib/api/types';
import type { SearchHistoryItem } from '@/lib/types/localStorage';
import { SEARCH_DEBOUNCE_MS, DEFAULT_PAGE_SIZE } from '@/lib/utils/constants';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFiltersType>({});
  const [searchType, setSearchType] = useState<SearchType>('hybrid');
  const [page, setPage] = useState(1);

  const { history, addSearch, removeSearch, clearHistory } = useSearchHistory();

  const debouncedQuery = useDebounce(query, SEARCH_DEBOUNCE_MS);

  const searchRequest = useMemo(() => {
    if (!debouncedQuery.trim()) return null;
    return {
      query: debouncedQuery,
      filters,
      search_type: searchType,
      limit: DEFAULT_PAGE_SIZE,
      offset: (page - 1) * DEFAULT_PAGE_SIZE,
    };
  }, [debouncedQuery, filters, searchType, page]);

  const { data, isLoading, error } = useSearch(searchRequest);

  const totalPages = data ? Math.ceil(data.total / DEFAULT_PAGE_SIZE) : 0;

  const handleQueryChange = (newQuery: string) => {
    setQuery(newQuery);
    setPage(1);
  };

  const handleFiltersChange = (newFilters: SearchFiltersType) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handleSearchTypeChange = (type: SearchType) => {
    setSearchType(type);
    setPage(1);
  };

  // Save search to history on submit (Enter key)
  const handleSearchSubmit = useCallback(() => {
    if (query.trim()) {
      addSearch(query, filters, searchType);
    }
  }, [query, filters, searchType, addSearch]);

  // Handle history item selection
  const handleHistorySelect = useCallback((item: SearchHistoryItem) => {
    setQuery(item.query);
    if (item.filters) setFilters(item.filters);
    if (item.searchType) setSearchType(item.searchType);
    setPage(1);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-text-primary">Search</h1>
        <p className="text-text-secondary">
          Search through biomedical literature using semantic, keyword, or hybrid search.
        </p>
      </div>

      {/* Search Bar */}
      <SearchBar
        value={query}
        onChange={handleQueryChange}
        onSubmit={handleSearchSubmit}
        history={history}
        onHistorySelect={handleHistorySelect}
        onHistoryRemove={removeSearch}
        onHistoryClear={clearHistory}
      />

      {/* Filters */}
      <SearchFilters
        filters={filters}
        searchType={searchType}
        onFiltersChange={handleFiltersChange}
        onSearchTypeChange={handleSearchTypeChange}
      />

      {/* Results */}
      <div className="space-y-4">
        {/* Results count */}
        {data && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-text-secondary">
              Found {data.total.toLocaleString()} results
              {data.query_metadata.took_ms && (
                <span className="ml-1">({data.query_metadata.took_ms}ms)</span>
              )}
            </p>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="rounded-md border border-danger/50 bg-danger/10 p-4 text-danger">
            {error.message || 'An error occurred while searching'}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && debouncedQuery && data?.results.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-lg font-medium text-text-primary">No results found</p>
            <p className="mt-1 text-text-secondary">
              Try adjusting your search terms or filters
            </p>
          </div>
        )}

        {/* Initial state */}
        {!query && !isLoading && (
          <div className="py-12 text-center">
            <p className="text-lg font-medium text-text-primary">
              Start searching
            </p>
            <p className="mt-1 text-text-secondary">
              Enter a query above to search through biomedical literature
            </p>
          </div>
        )}

        {/* Results list */}
        {data?.results && data.results.length > 0 && (
          <div className="space-y-4">
            {data.results.map((result) => (
              <SearchResultCard key={result.chunk_id} result={result} query={debouncedQuery} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  );
}
