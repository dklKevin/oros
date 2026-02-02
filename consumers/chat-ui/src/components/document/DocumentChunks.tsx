'use client';

import { useState } from 'react';
import { Card, Badge, Spinner } from '@/components/ui';
import { Pagination } from '@/components/search/Pagination';
import { useDocumentChunks } from '@/lib/hooks';
import { formatTokenCount } from '@/lib/utils/format';

interface DocumentChunksProps {
  documentId: string;
}

const CHUNKS_PER_PAGE = 10;

export function DocumentChunks({ documentId }: DocumentChunksProps) {
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useDocumentChunks(documentId, {
    limit: CHUNKS_PER_PAGE,
    offset: (page - 1) * CHUNKS_PER_PAGE,
  });

  const totalPages = data ? Math.ceil(data.total / CHUNKS_PER_PAGE) : 0;

  // Group chunks by section
  const chunksBySection = data?.chunks.reduce((acc, chunk) => {
    const section = chunk.section_title || 'Content';
    if (!acc[section]) {
      acc[section] = [];
    }
    acc[section].push(chunk);
    return acc;
  }, {} as Record<string, typeof data.chunks>);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-danger/50 bg-danger/10 p-4 text-danger">
        Failed to load document chunks
      </div>
    );
  }

  if (!data || data.chunks.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-text-secondary">No chunks available for this document</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-text-primary">
          Document Content
        </h2>
        <span className="text-sm text-text-secondary">
          {data.total} chunks total
        </span>
      </div>

      {/* Chunks grouped by section */}
      <div className="space-y-6">
        {chunksBySection && Object.entries(chunksBySection).map(([section, chunks]) => (
          <div key={section} className="space-y-3">
            {/* Section header */}
            <h3 className="text-sm font-medium uppercase tracking-wide text-text-secondary">
              {section}
            </h3>

            {/* Chunks */}
            {chunks.map((chunk) => (
              <Card key={chunk.id} padding="md">
                <div className="space-y-3">
                  {/* Chunk metadata */}
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Badge variant="default">Chunk #{chunk.chunk_index + 1}</Badge>
                    {chunk.token_count && (
                      <span>{formatTokenCount(chunk.token_count)}</span>
                    )}
                  </div>

                  {/* Chunk content */}
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
                    {chunk.content}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
