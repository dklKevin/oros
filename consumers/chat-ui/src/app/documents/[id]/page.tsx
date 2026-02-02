'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { DocumentHeader, DocumentChunks } from '@/components/document';
import { Spinner, SkeletonText, Card } from '@/components/ui';
import { useDocument } from '@/lib/hooks';

export default function DocumentPage() {
  const params = useParams();
  const documentId = params.id as string;

  const { data: document, isLoading, error } = useDocument(documentId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-accent-fg"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Search
        </Link>
        <Card>
          <div className="space-y-4">
            <div className="h-6 w-3/4 animate-pulse rounded bg-subtle" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-subtle" />
            <SkeletonText lines={4} />
          </div>
        </Card>
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-accent-fg"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Search
        </Link>
        <div className="rounded-md border border-danger/50 bg-danger/10 p-4 text-danger">
          {error.message || 'Failed to load document'}
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="space-y-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-accent-fg"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Search
        </Link>
        <div className="py-12 text-center">
          <p className="text-lg font-medium text-text-primary">Document not found</p>
          <p className="mt-1 text-text-secondary">
            The requested document could not be found
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-accent-fg"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Search
      </Link>

      {/* Document header */}
      <DocumentHeader document={document} />

      {/* Document chunks */}
      <DocumentChunks documentId={documentId} />
    </div>
  );
}
