import { ingestionApi } from './client';
import type {
  IngestRequest,
  IngestResponse,
  JobStatusResponse,
  HealthResponse,
} from './types';

export async function ingest(request: IngestRequest): Promise<IngestResponse> {
  return ingestionApi.post<IngestResponse>('/ingest', request);
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return ingestionApi.get<JobStatusResponse>(`/status/${jobId}`);
}

export async function getIngestionHealth(): Promise<HealthResponse> {
  return ingestionApi.get<HealthResponse>('/health');
}
