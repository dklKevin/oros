'use client';

import { Bookmark } from 'lucide-react';
import { useBookmarks } from '@/lib/hooks/useBookmarks';
import { Button } from './Button';

interface BookmarkButtonProps {
  documentId: string;
  title: string;
  doi?: string;
  authors?: string[];
  className?: string;
  size?: 'sm' | 'md';
}

export function BookmarkButton({
  documentId,
  title,
  doi,
  authors,
  className,
  size = 'sm',
}: BookmarkButtonProps) {
  const { isBookmarked, toggleBookmark } = useBookmarks();
  const bookmarked = isBookmarked(documentId);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggleBookmark({
      document_id: documentId,
      title,
      doi,
      authors,
    });
  };

  return (
    <Button
      variant="ghost"
      size={size}
      onClick={handleClick}
      className={className}
      aria-label={bookmarked ? 'Remove bookmark' : 'Add bookmark'}
      title={bookmarked ? 'Remove bookmark' : 'Add bookmark'}
    >
      <Bookmark
        className={`h-4 w-4 ${bookmarked ? 'fill-accent-fg text-accent-fg' : ''}`}
      />
    </Button>
  );
}
