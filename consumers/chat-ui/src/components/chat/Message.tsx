'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import type { ChatMessage } from '@/lib/api/types';

interface MessageProps {
  message: ChatMessage;
  onCitationClick?: (index: number) => void;
}

export function Message({ message, onCitationClick }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? 'bg-accent' : 'bg-subtle'
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-accent-fg" />
        )}
      </div>

      {/* Message content */}
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-accent text-white'
            : 'border border-border bg-surface text-text-primary'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Style links
                a: ({ href, children }) => (
                  <a
                    href={href}
                    className="text-accent-fg hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {children}
                  </a>
                ),
                // Style code blocks
                code: ({ className, children }) => {
                  const isInline = !className;
                  if (isInline) {
                    return (
                      <code className="rounded bg-subtle px-1.5 py-0.5 text-sm">
                        {children}
                      </code>
                    );
                  }
                  return (
                    <code className={`block overflow-x-auto rounded bg-canvas p-3 text-sm ${className}`}>
                      {children}
                    </code>
                  );
                },
                // Style lists
                ul: ({ children }) => <ul className="list-disc pl-4">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-4">{children}</ol>,
                // Style paragraphs
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
