import type { ApiError } from './types';

const RETRIEVAL_URL = process.env.NEXT_PUBLIC_RETRIEVAL_URL || 'http://localhost:8000';
const INGESTION_URL = process.env.NEXT_PUBLIC_INGESTION_URL || 'http://localhost:8001';

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | undefined>;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    try {
      const error: ApiError = await response.json();
      errorMessage = error.detail || errorMessage;
    } catch {
      // Use default error message
    }
    throw new ApiRequestError(errorMessage, response.status);
  }
  return response.json();
}

function buildUrl(base: string, path: string, params?: Record<string, string | number | undefined>): string {
  const url = new URL(path, base);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

export const retrievalApi = {
  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = buildUrl(RETRIEVAL_URL, path, options?.params);
    const response = await fetch(url, {
      ...options,
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body: unknown, options?: RequestOptions): Promise<T> {
    const url = buildUrl(RETRIEVAL_URL, path, options?.params);
    const response = await fetch(url, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: JSON.stringify(body),
    });
    return handleResponse<T>(response);
  },
};

export const ingestionApi = {
  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = buildUrl(INGESTION_URL, path, options?.params);
    const response = await fetch(url, {
      ...options,
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body: unknown, options?: RequestOptions): Promise<T> {
    const url = buildUrl(INGESTION_URL, path, options?.params);
    const response = await fetch(url, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      body: JSON.stringify(body),
    });
    return handleResponse<T>(response);
  },
};
