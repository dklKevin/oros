'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle } from 'lucide-react';
import { Button, Textarea, Spinner, Badge } from '@/components/ui';
import { Message } from './Message';
import { CitationsList } from './Citation';
import { useChat } from '@/lib/hooks';
import type { ChatMessage, Citation } from '@/lib/api/types';
import { formatScore } from '@/lib/utils/format';

interface ChatEntry {
  message: ChatMessage;
  citations?: Citation[];
  confidence?: number;
}

export function ChatContainer() {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { mutate: sendMessage, isPending, error } = useChat();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [history]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isPending) return;

    const userMessage: ChatMessage = { role: 'user', content: input.trim() };
    const newHistory = [...history, { message: userMessage }];
    setHistory(newHistory);
    setInput('');

    // Build conversation history for context
    const conversationHistory = newHistory
      .map((entry) => entry.message)
      .slice(-10); // Keep last 10 messages for context

    sendMessage(
      {
        query: userMessage.content,
        conversation_history: conversationHistory.slice(0, -1), // Exclude current message
      },
      {
        onSuccess: (response) => {
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: response.answer,
          };
          setHistory((prev) => [
            ...prev,
            {
              message: assistantMessage,
              citations: response.citations,
              confidence: response.confidence_score,
            },
          ]);
        },
        onError: () => {
          // Add error message to history
          const errorMessage: ChatMessage = {
            role: 'assistant',
            content: 'Sorry, I encountered an error processing your request. Please try again.',
          };
          setHistory((prev) => [...prev, { message: errorMessage }]);
        },
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const lastAssistantEntry = [...history].reverse().find(
    (entry) => entry.message.role === 'assistant' && entry.citations
  );

  return (
    <div className="flex h-[calc(100vh-12rem)] flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-6 pb-4">
          {/* Welcome message */}
          {history.length === 0 && (
            <div className="py-12 text-center">
              <h2 className="text-lg font-medium text-text-primary">
                Ask me about biomedical research
              </h2>
              <p className="mt-1 text-text-secondary">
                I can help answer questions using information from scientific literature
              </p>
            </div>
          )}

          {/* Message history */}
          {history.map((entry, index) => (
            <div key={index} className="space-y-3">
              <Message message={entry.message} />
              {entry.confidence !== undefined && entry.message.role === 'assistant' && (
                <div className="ml-11 flex items-center gap-2">
                  <Badge variant={entry.confidence > 0.7 ? 'success' : entry.confidence > 0.4 ? 'warning' : 'danger'}>
                    Confidence: {formatScore(entry.confidence)}
                  </Badge>
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {isPending && (
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-subtle">
                <Spinner size="sm" />
              </div>
              <span className="text-sm text-text-secondary">Thinking...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Citations panel */}
      {lastAssistantEntry?.citations && lastAssistantEntry.citations.length > 0 && (
        <div className="border-t border-border py-4">
          <CitationsList citations={lastAssistantEntry.citations} />
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-danger">
          <AlertCircle className="h-4 w-4" />
          {error.message || 'An error occurred'}
        </div>
      )}

      {/* Input area */}
      <form onSubmit={handleSubmit} className="border-t border-border pt-4">
        <div className="flex gap-3">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about biomedical research..."
            disabled={isPending}
            rows={2}
            className="resize-none"
          />
          <Button type="submit" disabled={!input.trim() || isPending} className="self-end">
            {isPending ? <Spinner size="sm" /> : <Send className="h-4 w-4" />}
            Send
          </Button>
        </div>
        <p className="mt-2 text-xs text-text-secondary">
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>
    </div>
  );
}
