'use client';

import { CheckCircle, XCircle, Clock, Loader2, RefreshCw } from 'lucide-react';
import { Card, Badge, Spinner } from '@/components/ui';
import { useJobStatus } from '@/lib/hooks';
import { PROCESSING_STATUS_LABELS } from '@/lib/utils/constants';
import type { ProcessingStatus } from '@/lib/api/types';

interface JobStatusCardProps {
  jobId: string;
  documentId: string;
  onRemove?: () => void;
}

const statusIcons: Record<ProcessingStatus, React.ReactNode> = {
  pending: <Clock className="h-5 w-5 text-text-secondary" />,
  processing: <Loader2 className="h-5 w-5 animate-spin text-accent-fg" />,
  completed: <CheckCircle className="h-5 w-5 text-success" />,
  failed: <XCircle className="h-5 w-5 text-danger" />,
  retrying: <RefreshCw className="h-5 w-5 animate-spin text-[#d29922]" />,
};

const statusVariants: Record<ProcessingStatus, 'default' | 'success' | 'danger' | 'warning' | 'accent'> = {
  pending: 'default',
  processing: 'accent',
  completed: 'success',
  failed: 'danger',
  retrying: 'warning',
};

export function JobStatusCard({ jobId, documentId, onRemove }: JobStatusCardProps) {
  const { data: status, isLoading, error } = useJobStatus(jobId);

  const progressPercent = status
    ? Math.round((status.completed_steps / Math.max(status.total_steps, 1)) * 100)
    : 0;

  if (isLoading && !status) {
    return (
      <Card>
        <div className="flex items-center gap-3">
          <Spinner size="sm" />
          <span className="text-sm text-text-secondary">Loading job status...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-text-primary">Job {jobId.slice(0, 8)}...</p>
            <p className="text-sm text-danger">Failed to fetch status</p>
          </div>
          {onRemove && (
            <button
              onClick={onRemove}
              className="text-sm text-text-secondary hover:text-text-primary"
            >
              Remove
            </button>
          )}
        </div>
      </Card>
    );
  }

  if (!status) return null;

  const isTerminal = status.status === 'completed' || status.status === 'failed';

  return (
    <Card>
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            {statusIcons[status.status]}
            <div>
              <p className="text-sm font-medium text-text-primary">
                Job {jobId.slice(0, 8)}...
              </p>
              <p className="text-xs text-text-secondary">
                Document: {documentId.slice(0, 8)}...
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={statusVariants[status.status]}>
              {PROCESSING_STATUS_LABELS[status.status] || status.status}
            </Badge>
            {isTerminal && onRemove && (
              <button
                onClick={onRemove}
                className="text-xs text-text-secondary hover:text-text-primary"
              >
                Remove
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        {!isTerminal && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-text-secondary">
              <span>{status.current_step || 'Processing...'}</span>
              <span>{progressPercent}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-subtle">
              <div
                className="h-full bg-accent transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="text-xs text-text-secondary">
              Step {status.completed_steps} of {status.total_steps}
            </p>
          </div>
        )}

        {/* Error message */}
        {status.error_message && (
          <div className="rounded-md border border-danger/50 bg-danger/10 p-2 text-xs text-danger">
            {status.error_message}
          </div>
        )}

        {/* Success message */}
        {status.status === 'completed' && (
          <div className="rounded-md border border-success/50 bg-success/10 p-2 text-xs text-success">
            Document processed successfully
          </div>
        )}
      </div>
    </Card>
  );
}
