'use client';

import { useState, useRef, useEffect } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui';
import { SearchHistoryDropdown } from './SearchHistoryDropdown';
import type { SearchHistoryItem } from '@/lib/types/localStorage';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  history?: SearchHistoryItem[];
  onHistorySelect?: (item: SearchHistoryItem) => void;
  onHistoryRemove?: (id: string) => void;
  onHistoryClear?: () => void;
}

export function SearchBar({
  value,
  onChange,
  onSubmit,
  placeholder = 'Search biomedical literature...',
  disabled,
  history = [],
  onHistorySelect,
  onHistoryRemove,
  onHistoryClear,
}: SearchBarProps) {
  const [isFocused, setIsFocused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Show dropdown when focused, empty input, and has history
  const showHistory = isFocused && !value.trim() && history.length > 0;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsFocused(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && onSubmit) {
      onSubmit();
    }
    if (e.key === 'Escape') {
      setIsFocused(false);
    }
  };

  const handleHistorySelect = (item: SearchHistoryItem) => {
    if (onHistorySelect) {
      onHistorySelect(item);
    }
    setIsFocused(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-text-secondary" />
      <Input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="pl-10 py-3 text-base"
      />
      {showHistory && onHistoryRemove && onHistoryClear && (
        <SearchHistoryDropdown
          history={history}
          onSelect={handleHistorySelect}
          onRemove={onHistoryRemove}
          onClearAll={onHistoryClear}
        />
      )}
    </div>
  );
}
