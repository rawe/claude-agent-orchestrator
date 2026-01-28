import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import { ToolCallBadge } from './ToolCallBadge';
import { TypingIndicator } from './TypingIndicator';
import type { ChatMessage as ChatMessageType, ToolCall } from '../types';

interface ChatMessageProps {
  message: ChatMessageType;
  currentToolCalls?: ToolCall[];
}

export function ChatMessage({ message, currentToolCalls = [] }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isPending = message.status === 'pending';
  const toolCalls = isPending ? currentToolCalls : message.toolCalls || [];

  // System messages render centered without avatar
  if (isSystem) {
    return (
      <div className="flex justify-center message-enter">
        <div
          className={`
            inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm
            ${isPending
              ? 'bg-blue-50 text-blue-600 border border-blue-200'
              : 'bg-gray-100 text-gray-600 border border-gray-200'
            }
          `}
        >
          {isPending && (
            <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          )}
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 message-enter ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`
          flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? 'bg-blue-600' : 'bg-gray-700'}
        `}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Tool calls for assistant */}
        {!isUser && toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {toolCalls.map((tool) => (
              <ToolCallBadge key={tool.id} tool={tool} />
            ))}
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`
            rounded-2xl px-4 py-2.5
            ${isUser
              ? 'bg-blue-600 text-white rounded-br-md'
              : 'bg-gray-100 text-gray-900 rounded-bl-md'
            }
          `}
        >
          {isPending && !message.content ? (
            <TypingIndicator />
          ) : (
            <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert' : ''}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`mt-1 text-xs text-gray-400 ${isUser ? 'text-right' : ''}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          {isPending && <span className="ml-2 text-blue-500">Processing...</span>}
        </div>
      </div>
    </div>
  );
}
