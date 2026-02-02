'use client';

import { ChatContainer } from '@/components/chat';

export default function ChatPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-text-primary">Chat</h1>
        <p className="text-text-secondary">
          Ask questions and get AI-powered answers with citations from biomedical literature.
        </p>
      </div>

      {/* Chat */}
      <ChatContainer />
    </div>
  );
}
