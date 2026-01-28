import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Send, Square } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, onStop, isLoading, disabled, placeholder }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    if (message.trim() && !isLoading && !disabled) {
      onSend(message);
      setMessage('');
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex items-end gap-3 p-4 bg-white border-t border-gray-200">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Type your message..."}
          disabled={disabled}
          rows={1}
          className={`
            w-full px-4 py-3 pr-12
            bg-gray-50 border border-gray-200 rounded-2xl
            resize-none overflow-hidden
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            placeholder-gray-400
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-shadow
          `}
        />
      </div>

      {/* Send/Stop button */}
      {isLoading ? (
        <button
          onClick={onStop}
          className={`
            flex-shrink-0 w-12 h-12 rounded-full
            bg-red-500 hover:bg-red-600
            flex items-center justify-center
            text-white
            transition-colors
            shadow-lg shadow-red-500/25
          `}
          title="Stop"
        >
          <Square className="w-5 h-5" fill="currentColor" />
        </button>
      ) : (
        <button
          onClick={handleSubmit}
          disabled={!message.trim() || disabled}
          className={`
            flex-shrink-0 w-12 h-12 rounded-full
            ${message.trim() && !disabled
              ? 'bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-600/25'
              : 'bg-gray-200 cursor-not-allowed'
            }
            flex items-center justify-center
            text-white
            transition-all
          `}
          title="Send"
        >
          <Send className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}
