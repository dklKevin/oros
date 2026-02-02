'use client';

import { useCallback } from 'react';
import { useLocalStorage } from './useLocalStorage';
import type { BookmarkedDocument } from '@/lib/types/localStorage';
import { BOOKMARKS_STORAGE_KEY } from '@/lib/utils/constants';

/**
 * Hook for managing document bookmarks in localStorage.
 */
export function useBookmarks() {
  const [bookmarks, setBookmarks, clearBookmarks] = useLocalStorage<BookmarkedDocument[]>(
    BOOKMARKS_STORAGE_KEY,
    []
  );

  const addBookmark = useCallback(
    (document: Omit<BookmarkedDocument, 'bookmarked_at'>) => {
      setBookmarks((prev) => {
        // Check if already bookmarked
        if (prev.some((b) => b.document_id === document.document_id)) {
          return prev;
        }
        return [
          {
            ...document,
            bookmarked_at: Date.now(),
          },
          ...prev,
        ];
      });
    },
    [setBookmarks]
  );

  const removeBookmark = useCallback(
    (documentId: string) => {
      setBookmarks((prev) => prev.filter((b) => b.document_id !== documentId));
    },
    [setBookmarks]
  );

  const toggleBookmark = useCallback(
    (document: Omit<BookmarkedDocument, 'bookmarked_at'>) => {
      const isBookmarked = bookmarks.some((b) => b.document_id === document.document_id);
      if (isBookmarked) {
        removeBookmark(document.document_id);
      } else {
        addBookmark(document);
      }
    },
    [bookmarks, addBookmark, removeBookmark]
  );

  const isBookmarked = useCallback(
    (documentId: string) => {
      return bookmarks.some((b) => b.document_id === documentId);
    },
    [bookmarks]
  );

  return {
    bookmarks,
    addBookmark,
    removeBookmark,
    toggleBookmark,
    isBookmarked,
    clearBookmarks,
  };
}
