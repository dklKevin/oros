'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Upload } from 'lucide-react';
import { Button, Input, Card } from '@/components/ui';
import { useIngest } from '@/lib/hooks';

const ingestSchema = z.object({
  source_url: z.string().url('Please enter a valid URL'),
  document_type: z.enum(['auto', 'pubmed_xml', 'pdf']),
  priority: z.number().min(0).max(10),
});

type IngestFormData = z.infer<typeof ingestSchema>;

interface IngestFormProps {
  onSuccess: (jobId: string, documentId: string) => void;
}

export function IngestForm({ onSuccess }: IngestFormProps) {
  const { mutate: submitIngest, isPending, error } = useIngest();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<IngestFormData>({
    resolver: zodResolver(ingestSchema),
    defaultValues: {
      source_url: '',
      document_type: 'auto',
      priority: 0,
    },
  });

  const onSubmit = (data: IngestFormData) => {
    submitIngest(data, {
      onSuccess: (response) => {
        onSuccess(response.job_id, response.document_id);
        reset();
      },
    });
  };

  return (
    <Card>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <h2 className="text-lg font-medium text-text-primary">Ingest New Document</h2>

        {/* URL Input */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-text-secondary">
            Document URL
          </label>
          <Input
            type="url"
            placeholder="https://example.com/document.pdf"
            {...register('source_url')}
            error={errors.source_url?.message}
          />
        </div>

        {/* Document Type */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-text-secondary">
            Document Type
          </label>
          <select
            {...register('document_type')}
            className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-accent-fg focus:outline-none focus:ring-1 focus:ring-accent-fg"
          >
            <option value="auto">Auto-detect</option>
            <option value="pubmed_xml">PubMed XML</option>
            <option value="pdf">PDF</option>
          </select>
        </div>

        {/* Priority */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-text-secondary">
            Priority (0-10)
          </label>
          <Input
            type="number"
            min={0}
            max={10}
            {...register('priority', { valueAsNumber: true })}
            error={errors.priority?.message}
          />
          <p className="mt-1 text-xs text-text-secondary">
            Higher priority jobs are processed first
          </p>
        </div>

        {/* Error display */}
        {error && (
          <div className="rounded-md border border-danger/50 bg-danger/10 p-3 text-sm text-danger">
            {error.message || 'Failed to submit ingestion job'}
          </div>
        )}

        {/* Submit button */}
        <Button type="submit" loading={isPending} className="w-full">
          <Upload className="h-4 w-4" />
          Submit for Ingestion
        </Button>
      </form>
    </Card>
  );
}
