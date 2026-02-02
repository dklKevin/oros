'use client';

import { useMutation } from '@tanstack/react-query';
import { chat } from '@/lib/api/retrieval';
import type { ChatRequest, ChatResponse } from '@/lib/api/types';

export function useChat() {
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: chat,
  });
}
