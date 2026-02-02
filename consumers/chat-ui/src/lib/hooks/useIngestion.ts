'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { ingest, getJobStatus } from '@/lib/api/ingestion';
import type { IngestRequest, IngestResponse, JobStatusResponse } from '@/lib/api/types';
import { JOB_POLL_INTERVAL_MS } from '@/lib/utils/constants';

export function useIngest() {
  return useMutation<IngestResponse, Error, IngestRequest>({
    mutationFn: ingest,
  });
}

export function useJobStatus(jobId: string | undefined, options?: { enabled?: boolean }) {
  return useQuery<JobStatusResponse>({
    queryKey: ['job-status', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId && options?.enabled !== false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') {
        return false;
      }
      return JOB_POLL_INTERVAL_MS;
    },
  });
}
