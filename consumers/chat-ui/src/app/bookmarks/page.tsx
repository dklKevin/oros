'use client';

import Link from 'next/link';
import { Bookmark, Trash2, ExternalLink } from 'lucide-react';
import { useBookmarks } from '@/lib/hooks/useBookmarks';
import { Card, Button } from '@/components/ui';
import { getDoiUrl } from '@/lib/utils/format';

export default function BookmarksPage() {
  const { bookmarks, removeBookmark, clearBookmarks } = useBookmarks();

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatAuthors = (authors?: string[]) => {
    if (!authors || authors.length === 0) return null;
    if (authors.length === 1) return authors[0];
    if (authors.length === 2) return `${authors[0]} and ${authors[1]}`;
    return `${authors[0]} et al.`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-text-primary">Bookmarks</h1>
          <p className="text-text-secondary">
            {bookmarks.length === 0
              ? 'No bookmarked documents yet'
              : `${bookmarks.length} bookmarked document${bookmarks.length === 1 ? '' : 's'}`}
          </p>
        </div>
        {bookmarks.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearBookmarks}
            className="text-text-secondary hover:text-danger"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Clear all
          </Button>
        )}
      </div>

      {/* Empty state */}
      {bookmarks.length === 0 && (
        <div className="py-12 text-center">
          <Bookmark className="mx-auto h-12 w-12 text-text-secondary" />
          <h2 className="mt-4 text-lg font-medium text-text-primary">No bookmarks yet</h2>
          <p className="mt-2 text-text-secondary">
            Bookmark documents from search results or document pages to save them here.
          </p>
          <Link href="/">
            <Button variant="primary" className="mt-4">
              Start searching
            </Button>
          </Link>
        </div>
      )}

      {/* Bookmarks list */}
      {bookmarks.length > 0 && (
        <div className="space-y-4">
          {bookmarks.map((bookmark) => (
            <Card key={bookmark.document_id} className="transition-colors hover:border-accent-fg/50">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/documents/${bookmark.document_id}`}
                    className="text-base font-medium text-text-primary hover:text-accent-fg hover:underline"
                  >
                    {bookmark.title}
                  </Link>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-text-secondary">
                    {formatAuthors(bookmark.authors) && (
                      <span>{formatAuthors(bookmark.authors)}</span>
                    )}
                    {bookmark.doi && (
                      <>
                        {formatAuthors(bookmark.authors) && (
                          <span className="text-border">•</span>
                        )}
                        <a
                          href={getDoiUrl(bookmark.doi) ?? '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 hover:text-accent-fg"
                        >
                          DOI: {bookmark.doi}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-text-secondary">
                    Bookmarked on {formatDate(bookmark.bookmarked_at)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeBookmark(bookmark.document_id)}
                  className="shrink-0 text-text-secondary hover:text-danger"
                  aria-label="Remove bookmark"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
