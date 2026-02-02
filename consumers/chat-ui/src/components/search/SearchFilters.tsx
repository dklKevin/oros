'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { Button, Input } from '@/components/ui';
import type { SearchFilters as SearchFiltersType, SearchType } from '@/lib/api/types';
import { SEARCH_TYPES } from '@/lib/utils/constants';

interface SearchFiltersProps {
  filters: SearchFiltersType;
  searchType: SearchType;
  onFiltersChange: (filters: SearchFiltersType) => void;
  onSearchTypeChange: (type: SearchType) => void;
}

export function SearchFilters({
  filters,
  searchType,
  onFiltersChange,
  onSearchTypeChange,
}: SearchFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasActiveFilters = filters.date_from || filters.date_to || (filters.journals && filters.journals.length > 0);

  const clearFilters = () => {
    onFiltersChange({});
  };

  return (
    <div className="rounded-md border border-border bg-surface">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-primary">Filters</span>
          {hasActiveFilters && (
            <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-white">Active</span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-text-secondary" />
        ) : (
          <ChevronDown className="h-4 w-4 text-text-secondary" />
        )}
      </button>

      {isExpanded && (
        <div className="border-t border-border px-4 py-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* Search Type */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                Search Type
              </label>
              <select
                value={searchType}
                onChange={(e) => onSearchTypeChange(e.target.value as SearchType)}
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-accent-fg focus:outline-none focus:ring-1 focus:ring-accent-fg"
              >
                {SEARCH_TYPES.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* Date From */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                From Date
              </label>
              <Input
                type="date"
                value={filters.date_from || ''}
                onChange={(e) =>
                  onFiltersChange({ ...filters, date_from: e.target.value || undefined })
                }
              />
            </div>

            {/* Date To */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                To Date
              </label>
              <Input
                type="date"
                value={filters.date_to || ''}
                onChange={(e) =>
                  onFiltersChange({ ...filters, date_to: e.target.value || undefined })
                }
              />
            </div>

            {/* Journals */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-secondary">
                Journal (comma-separated)
              </label>
              <Input
                type="text"
                placeholder="e.g., Nature, Science"
                value={filters.journals?.join(', ') || ''}
                onChange={(e) => {
                  const value = e.target.value;
                  const journals = value ? value.split(',').map((j) => j.trim()).filter(Boolean) : undefined;
                  onFiltersChange({ ...filters, journals });
                }}
              />
            </div>
          </div>

          {hasActiveFilters && (
            <div className="mt-4 flex justify-end">
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <X className="h-4 w-4" />
                Clear Filters
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
