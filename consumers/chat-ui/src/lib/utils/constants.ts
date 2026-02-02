export const SEARCH_DEBOUNCE_MS = 300;
export const DEFAULT_PAGE_SIZE = 10;
export const CHAT_MAX_CHUNKS = 5;
export const JOB_POLL_INTERVAL_MS = 2000;

// localStorage keys
export const SEARCH_HISTORY_KEY = 'oros_search_history';
export const SEARCH_HISTORY_MAX_ITEMS = 10;
export const BOOKMARKS_STORAGE_KEY = 'oros_bookmarks';

export const SEARCH_TYPES = [
  { value: 'hybrid', label: 'Hybrid Search' },
  { value: 'vector', label: 'Semantic Search' },
  { value: 'keyword', label: 'Keyword Search' },
] as const;

export const PROCESSING_STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
  retrying: 'Retrying',
};
