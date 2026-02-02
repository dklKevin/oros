'use client';

import { ExternalLink, Calendar, BookOpen, Award } from 'lucide-react';
import { Badge, Card, BookmarkButton } from '@/components/ui';
import type { Document } from '@/lib/api/types';
import { formatDate, formatAuthors, formatScore, getDoiUrl, getPubMedUrl } from '@/lib/utils/format';
import { PROCESSING_STATUS_LABELS } from '@/lib/utils/constants';

interface DocumentHeaderProps {
  document: Document;
}

export function DocumentHeader({ document }: DocumentHeaderProps) {
  const doiUrl = getDoiUrl(document.doi);
  const pubmedUrl = getPubMedUrl(document.pmcid);

  const statusVariant = document.processing_status === 'completed' ? 'success' :
    document.processing_status === 'failed' ? 'danger' :
    document.processing_status === 'processing' ? 'warning' : 'default';

  return (
    <Card>
      <div className="space-y-4">
        {/* Title and status */}
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-xl font-bold text-text-primary">{document.title}</h1>
          <div className="flex shrink-0 items-center gap-2">
            <BookmarkButton
              documentId={document.id}
              title={document.title}
              doi={document.doi}
              authors={document.authors?.map((a) => a.name)}
              size="md"
            />
            {document.quality_score !== undefined && document.quality_score !== null && (
              <Badge variant="accent" className="flex items-center gap-1">
                <Award className="h-3 w-3" />
                Quality: {formatScore(document.quality_score)}
              </Badge>
            )}
            <Badge variant={statusVariant}>
              {PROCESSING_STATUS_LABELS[document.processing_status] || document.processing_status}
            </Badge>
          </div>
        </div>

        {/* Authors */}
        {document.authors && document.authors.length > 0 && (
          <p className="text-text-secondary">{formatAuthors(document.authors)}</p>
        )}

        {/* Metadata row */}
        <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
          {document.journal && (
            <span className="flex items-center gap-1">
              <BookOpen className="h-4 w-4" />
              {document.journal}
            </span>
          )}
          {document.publication_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {formatDate(document.publication_date)}
            </span>
          )}
          {document.article_type && (
            <Badge variant="default">{document.article_type}</Badge>
          )}
        </div>

        {/* Abstract */}
        {document.abstract && (
          <div className="space-y-2 border-t border-border pt-4">
            <h2 className="text-sm font-medium uppercase text-text-secondary">Abstract</h2>
            <p className="text-sm leading-relaxed text-text-primary">{document.abstract}</p>
          </div>
        )}

        {/* External links */}
        <div className="flex flex-wrap gap-3 border-t border-border pt-4">
          {document.doi && (
            <a
              href={doiUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-accent-fg hover:underline"
            >
              DOI: {document.doi}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {document.pmcid && (
            <a
              href={pubmedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-accent-fg hover:underline"
            >
              {document.pmcid}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {document.pmid && (
            <a
              href={`https://pubmed.ncbi.nlm.nih.gov/${document.pmid}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-accent-fg hover:underline"
            >
              PMID: {document.pmid}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </Card>
  );
}
