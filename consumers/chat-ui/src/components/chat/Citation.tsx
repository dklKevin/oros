'use client';

import Link from 'next/link';
import { ExternalLink, FileText } from 'lucide-react';
import { Card, Badge } from '@/components/ui';
import type { Citation as CitationType } from '@/lib/api/types';
import { formatScore, getDoiUrl, getPubMedUrl } from '@/lib/utils/format';

interface CitationProps {
  citation: CitationType;
  index: number;
}

export function Citation({ citation, index }: CitationProps) {
  const doiUrl = getDoiUrl(citation.doi);
  const pubmedUrl = getPubMedUrl(citation.pmcid);

  return (
    <Card padding="sm" className="transition-colors hover:border-accent-fg/50">
      <div className="flex items-start gap-3">
        {/* Index badge */}
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-medium text-white">
          {index + 1}
        </div>

        {/* Content */}
        <div className="flex-1 space-y-2">
          <Link
            href={`/documents/${citation.document_id}`}
            className="line-clamp-2 text-sm font-medium text-text-primary hover:text-accent-fg hover:underline"
          >
            {citation.title}
          </Link>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="accent" className="text-xs">
              Relevance: {formatScore(citation.relevance_score)}
            </Badge>

            {citation.doi && (
              <a
                href={doiUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-text-secondary hover:text-accent-fg"
              >
                DOI
                <ExternalLink className="h-3 w-3" />
              </a>
            )}

            {citation.pmcid && (
              <a
                href={pubmedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-text-secondary hover:text-accent-fg"
              >
                PubMed
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

interface CitationsListProps {
  citations: CitationType[];
}

export function CitationsList({ citations }: CitationsListProps) {
  if (citations.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-medium text-text-secondary">
        <FileText className="h-4 w-4" />
        Sources ({citations.length})
      </h3>
      <div className="space-y-2">
        {citations.map((citation, index) => (
          <Citation key={citation.chunk_id} citation={citation} index={index} />
        ))}
      </div>
    </div>
  );
}
