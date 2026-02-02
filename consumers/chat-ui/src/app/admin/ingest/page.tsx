'use client';

import { useState } from 'react';
import { IngestForm, JobStatusCard } from '@/components/ingestion';

interface Job {
  jobId: string;
  documentId: string;
}

export default function IngestPage() {
  const [jobs, setJobs] = useState<Job[]>([]);

  const handleNewJob = (jobId: string, documentId: string) => {
    setJobs((prev) => [{ jobId, documentId }, ...prev]);
  };

  const handleRemoveJob = (jobId: string) => {
    setJobs((prev) => prev.filter((job) => job.jobId !== jobId));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-text-primary">Document Ingestion</h1>
        <p className="text-text-secondary">
          Submit documents for processing and track their ingestion status.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Ingest form */}
        <div>
          <IngestForm onSuccess={handleNewJob} />
        </div>

        {/* Jobs list */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-text-primary">
            Active Jobs {jobs.length > 0 && `(${jobs.length})`}
          </h2>

          {jobs.length === 0 ? (
            <div className="rounded-md border border-border bg-surface p-6 text-center">
              <p className="text-text-secondary">No active jobs</p>
              <p className="mt-1 text-sm text-text-secondary">
                Submit a document to see job progress here
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <JobStatusCard
                  key={job.jobId}
                  jobId={job.jobId}
                  documentId={job.documentId}
                  onRemove={() => handleRemoveJob(job.jobId)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
