'use client';

import { Clock, X, Trash2 } from 'lucide-react';
import type { SearchHistoryItem } from '@/lib/types/localStorage';
import { Button } from '@/components/ui';

interface SearchHistoryDropdownProps {
  history: SearchHistoryItem[];
  onSelect: (item: SearchHistoryItem) => void;
  onRemove: (id: string) => void;
  onClearAll: () => void;
}

export function SearchHistoryDropdown({
  history,
  onSelect,
  onRemove,
  onClearAll,
}: SearchHistoryDropdownProps) {
  if (history.length === 0) {
    return null;
  }

  const formatTimeAgo = (timestamp: number): string => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded-md border border-border bg-surface shadow-lg">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-xs font-medium text-text-secondary">Recent Searches</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onClearAll();
          }}
          className="h-6 px-2 text-xs text-text-secondary hover:text-danger"
        >
          <Trash2 className="mr-1 h-3 w-3" />
          Clear all
        </Button>
      </div>
      <ul className="max-h-64 overflow-y-auto py-1">
        {history.map((item) => (
          <li key={item.id} className="group relative">
            <button
              type="button"
              onClick={() => onSelect(item)}
              className="flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-subtle"
            >
              <Clock className="h-4 w-4 shrink-0 text-text-secondary" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-text-primary">{item.query}</p>
                <p className="text-xs text-text-secondary">{formatTimeAgo(item.timestamp)}</p>
              </div>
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onRemove(item.id);
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 opacity-0 transition-opacity hover:bg-danger/20 hover:text-danger group-hover:opacity-100"
              aria-label={`Remove "${item.query}" from history`}
            >
              <X className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
