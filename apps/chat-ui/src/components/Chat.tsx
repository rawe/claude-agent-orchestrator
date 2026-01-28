import { useRef, useEffect } from 'react';
import { MessageSquare, Plus, Wifi, WifiOff, AlertCircle } from 'lucide-react';
import { useChat } from '../contexts/ChatContext';
import { useSSE } from '../contexts/SSEContext';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { config } from '../config';

export function Chat() {
  const { state, sendMessage, stopAgent, resetChat, initializeChat } = useChat();
  const { connected } = useSSE();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.currentToolCalls]);

  const hasMessages = state.messages.length > 0;

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
            <MessageSquare className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">{config.appTitle}</h1>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              {connected ? (
                <>
                  <Wifi className="w-3 h-3 text-green-500" />
                  <span>Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 text-red-500" />
                  <span>Disconnected</span>
                </>
              )}
              {state.agentStatus !== 'idle' && (
                <>
                  <span className="text-gray-300">|</span>
                  <span className={`
                    ${state.agentStatus === 'running' ? 'text-blue-500' : ''}
                    ${state.agentStatus === 'finished' ? 'text-green-500' : ''}
                    ${state.agentStatus === 'error' ? 'text-red-500' : ''}
                  `}>
                    {state.agentStatus.charAt(0).toUpperCase() + state.agentStatus.slice(1)}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* New chat button */}
        {hasMessages && (
          <button
            onClick={resetChat}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg
              bg-gray-100 hover:bg-gray-200 text-gray-700
              transition-colors
            `}
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm font-medium">New Chat</span>
          </button>
        )}
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {!state.isInitialized ? (
          // Uninitialized state - show prominent Start button
          <div className="flex flex-col items-center justify-center h-full px-4 text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center mb-6">
              <MessageSquare className="w-10 h-10 text-blue-500" />
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">
              Welcome to {config.appTitle}
            </h2>
            <p className="text-gray-500 max-w-md mb-8">
              Click the button below to start a new conversation with the AI assistant.
            </p>
            <button
              onClick={initializeChat}
              disabled={!connected}
              className={`
                flex items-center gap-3 px-8 py-4 rounded-xl
                text-lg font-semibold
                transition-all duration-200
                ${connected
                  ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-600/30 hover:shadow-xl hover:shadow-blue-600/40 hover:-translate-y-0.5'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }
              `}
            >
              <Plus className="w-6 h-6" />
              <span>Start New Chat</span>
            </button>
            {!connected && (
              <p className="mt-4 text-sm text-gray-400">
                Waiting for connection...
              </p>
            )}
          </div>
        ) : !hasMessages ? (
          // Initialized but no messages yet (brief loading state)
          <div className="flex flex-col items-center justify-center h-full px-4 text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center mb-6">
              <MessageSquare className="w-10 h-10 text-blue-500" />
            </div>
            <p className="text-gray-500">Initializing session...</p>
          </div>
        ) : (
          // Messages list
          <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
            {state.messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                currentToolCalls={
                  message.id === state.pendingMessageId ? state.currentToolCalls : undefined
                }
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error banner */}
      {state.error && (
        <div className="mx-4 mb-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{state.error}</p>
          <button
            onClick={() => resetChat()}
            className="ml-auto text-sm text-red-600 hover:text-red-800 font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input area */}
      <ChatInput
        onSend={sendMessage}
        onStop={stopAgent}
        isLoading={state.isLoading}
        disabled={!connected || !state.isInitialized}
        placeholder={!state.isInitialized ? "Click 'Start New Chat' to begin..." : "Type your message..."}
      />
    </div>
  );
}
