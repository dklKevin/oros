'use client';

import Link from 'next/link';
import { ExternalLink } from 'lucide-react';
import { Card, Badge, BookmarkButton } from '@/components/ui';
import type { SearchResult } from '@/lib/api/types';
import { formatDate, formatAuthors, formatScore, truncateText, getDoiUrl, getPubMedUrl } from '@/lib/utils/format';

interface SearchResultCardProps {
  result: SearchResult;
  query?: string;
}

export function SearchResultCard({ result, query }: SearchResultCardProps) {
  const doiUrl = getDoiUrl(result.metadata.doi);
  const pubmedUrl = getPubMedUrl(result.metadata.pmcid);

  return (
    <Card className="transition-colors hover:border-accent-fg/50">
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <Link
            href={`/documents/${result.document_id}`}
            className="text-base font-medium text-text-primary hover:text-accent-fg hover:underline"
          >
            {result.title}
          </Link>
          <div className="flex shrink-0 items-center gap-2">
            <BookmarkButton
              documentId={result.document_id}
              title={result.title}
              doi={result.metadata.doi}
              authors={result.metadata.authors}
            />
            <Badge variant="accent">
              {formatScore(result.score)}
            </Badge>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex flex-wrap items-center gap-2 text-sm text-text-secondary">
          <span>{formatAuthors(result.metadata.authors)}</span>
          {result.metadata.journal && (
            <>
              <span className="text-border">•</span>
              <span>{result.metadata.journal}</span>
            </>
          )}
          {result.metadata.publication_date && (
            <>
              <span className="text-border">•</span>
              <span>{formatDate(result.metadata.publication_date)}</span>
            </>
          )}
        </div>

        {/* Content snippet */}
        {result.section_title && (
          <div className="text-xs font-medium uppercase text-text-secondary">
            {result.section_title}
          </div>
        )}
        <p className="text-sm text-text-secondary leading-relaxed">
          {truncateText(result.content, 300)}
        </p>

        {/* Links */}
        <div className="flex flex-wrap gap-2">
          {result.metadata.doi && (
            <Badge variant="default">
              <a
                href={doiUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-accent-fg"
              >
                DOI: {result.metadata.doi}
                <ExternalLink className="h-3 w-3" />
              </a>
            </Badge>
          )}
          {result.metadata.pmcid && (
            <Badge variant="default">
              <a
                href={pubmedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 hover:text-accent-fg"
              >
                {result.metadata.pmcid}
                <ExternalLink className="h-3 w-3" />
              </a>
            </Badge>
          )}
        </div>
      </div>
    </Card>
  );
}
