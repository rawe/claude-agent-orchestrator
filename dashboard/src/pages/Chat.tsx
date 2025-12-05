import { useEffect, useRef, useState } from 'react';
import { chatService } from '@/services/chatService';
import type { Agent, Session } from '@/types';
import { useNotification, useWebSocket, useChat } from '@/contexts';
import { useSessions } from '@/hooks/useSessions';
import { Button, Spinner } from '@/components/common';
import { SessionSelector } from '@/components/features/chat';
import { Send, Bot, User, RefreshCw, Wifi, WifiOff, Wrench, CheckCircle2, XCircle, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ToolCall } from '@/contexts/ChatContext';

// Use ToolCall type from context (imported as ToolCall)

// Truncate long strings for display
function truncateString(str: string, maxLength: number = 500): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '... (truncated)';
}

// Format JSON for display
function formatJson(data: unknown): string {
  try {
    const str = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    return truncateString(str, 1000);
  } catch {
    return String(data);
  }
}

// Generate markdown for tool call
function toolCallToMarkdown(tool: ToolCall): string {
  let md = `## Tool: ${tool.name}\n\n`;
  md += `**Status:** ${tool.status}\n\n`;

  if (tool.input && Object.keys(tool.input).length > 0) {
    md += `### Input\n\n\`\`\`json\n${JSON.stringify(tool.input, null, 2)}\n\`\`\`\n\n`;
  }

  if (tool.error) {
    md += `### Error\n\n\`\`\`\n${tool.error}\n\`\`\`\n`;
  } else if (tool.output !== undefined && tool.output !== null) {
    const outputStr = typeof tool.output === 'string' ? tool.output : JSON.stringify(tool.output, null, 2);
    md += `### Output\n\n\`\`\`\n${outputStr}\n\`\`\`\n`;
  }

  return md;
}

// Tool call badge with hover popover
function ToolCallBadge({ tool }: { tool: ToolCall }) {
  const [showPopover, setShowPopover] = useState(false);
  const [position, setPosition] = useState<{ top: boolean; left: boolean }>({ top: true, left: true });
  const [copied, setCopied] = useState(false);
  const hideTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const showTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const badgeRef = useRef<HTMLSpanElement>(null);

  const calculatePosition = () => {
    if (!badgeRef.current) return;

    const rect = badgeRef.current.getBoundingClientRect();
    const popoverWidth = 384; // w-96 = 24rem = 384px
    const popoverHeight = 300; // approximate max height

    // Check if there's enough space above
    const spaceAbove = rect.top;
    const spaceBelow = window.innerHeight - rect.bottom;
    const showOnTop = spaceAbove > popoverHeight || spaceAbove > spaceBelow;

    // Check if there's enough space to the left
    const spaceRight = window.innerWidth - rect.left;
    const showOnLeft = spaceRight >= popoverWidth;

    setPosition({ top: showOnTop, left: showOnLeft });
  };

  const clearTimeouts = () => {
    if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);
    if (showTimeoutRef.current) clearTimeout(showTimeoutRef.current);
  };

  const handleMouseEnter = () => {
    clearTimeouts();
    calculatePosition();
    showTimeoutRef.current = setTimeout(() => setShowPopover(true), 200);
  };

  const handleMouseLeave = () => {
    clearTimeouts();
    hideTimeoutRef.current = setTimeout(() => setShowPopover(false), 150);
  };

  const handlePopoverMouseEnter = () => {
    clearTimeouts();
  };

  const handlePopoverMouseLeave = () => {
    clearTimeouts();
    hideTimeoutRef.current = setTimeout(() => setShowPopover(false), 150);
  };

  const handleCopy = async () => {
    const markdown = toolCallToMarkdown(tool);
    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative inline-block">
      <span
        ref={badgeRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full cursor-default transition-all ${
          tool.status === 'running'
            ? 'bg-blue-100 text-blue-700'
            : tool.status === 'completed'
            ? 'bg-emerald-100 text-emerald-700'
            : 'bg-red-100 text-red-700'
        }`}
      >
        {tool.status === 'running' ? (
          <Wrench className="w-3 h-3 animate-pulse" />
        ) : tool.status === 'completed' ? (
          <CheckCircle2 className="w-3 h-3" />
        ) : (
          <XCircle className="w-3 h-3" />
        )}
        {tool.name}
      </span>

      {/* Hover Popover */}
      {showPopover && (
        <div
          onMouseEnter={handlePopoverMouseEnter}
          onMouseLeave={handlePopoverMouseLeave}
          className={`absolute z-50 w-96 max-w-[90vw] ${
            position.top ? 'bottom-full mb-2' : 'top-full mt-2'
          } ${
            position.left ? 'left-0' : 'right-0'
          }`}
        >
          <div className="bg-gray-900 text-gray-100 rounded-lg shadow-xl border border-gray-700 overflow-hidden max-h-80">
            {/* Header */}
            <div className="px-3 py-2 bg-gray-800 border-b border-gray-700 flex items-center gap-2">
              <Wrench className="w-4 h-4 text-gray-400" />
              <span className="font-medium truncate">{tool.name}</span>
              <span className={`ml-auto flex-shrink-0 text-xs px-1.5 py-0.5 rounded ${
                tool.status === 'completed' ? 'bg-emerald-900 text-emerald-300' : 'bg-red-900 text-red-300'
              }`}>
                {tool.status}
              </span>
              <button
                onClick={handleCopy}
                className="flex-shrink-0 p-1 rounded hover:bg-gray-700 transition-colors"
                title="Copy as Markdown"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-400 hover:text-gray-200" />
                )}
              </button>
            </div>

            <div className="overflow-y-auto max-h-64">
              {/* Input Section */}
              {tool.input && Object.keys(tool.input).length > 0 && (
                <div className="px-3 py-2 border-b border-gray-700">
                  <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Input</div>
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words max-h-28 overflow-y-auto font-mono bg-gray-950 rounded p-2">
                    {formatJson(tool.input)}
                  </pre>
                </div>
              )}

              {/* Output/Error Section */}
              {tool.error ? (
                <div className="px-3 py-2">
                  <div className="text-xs font-medium text-red-400 uppercase tracking-wide mb-1">Error</div>
                  <pre className="text-xs text-red-300 whitespace-pre-wrap break-words max-h-28 overflow-y-auto font-mono bg-red-950 rounded p-2">
                    {truncateString(tool.error, 1000)}
                  </pre>
                </div>
              ) : tool.output !== undefined && tool.output !== null ? (
                <div className="px-3 py-2">
                  <div className="text-xs font-medium text-emerald-400 uppercase tracking-wide mb-1">Output</div>
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words max-h-28 overflow-y-auto font-mono bg-gray-950 rounded p-2">
                    {formatJson(tool.output)}
                  </pre>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function Chat() {
  const { showError } = useNotification();
  const { connected } = useWebSocket();
  const {
    state,
    setMessages,
    setSessionName,
    setSessionId,
    setSelectedBlueprint,
    setAgentStatus,
    setIsLoading,
    setPendingMessageId,
    resetChat,
    linkToSession,
    startNewChat,
    isSessionActive,
  } = useChat();

  const { sessions } = useSessions();
  const [blueprints, setBlueprints] = useState<Agent[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoadingBlueprints, setIsLoadingBlueprints] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load blueprints on mount
  useEffect(() => {
    loadBlueprints();
  }, []);

  // Scroll to bottom when messages or tool calls change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.currentToolCalls]);

  const loadBlueprints = async () => {
    setIsLoadingBlueprints(true);
    try {
      const response = await chatService.listBlueprints();
      setBlueprints(response.blueprints);
    } catch (err) {
      showError('Failed to load agent blueprints');
      console.error(err);
    } finally {
      setIsLoadingBlueprints(false);
    }
  };

  const generateMessageId = () => {
    return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
  };

  const handleSendMessage = async () => {
    const prompt = inputValue.trim();
    if (!prompt || state.isLoading) return;

    // Add user message
    const userMessage = {
      id: generateMessageId(),
      role: 'user' as const,
      content: prompt,
      timestamp: new Date(),
      status: 'complete' as const,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Add pending assistant message
    const assistantMessageId = generateMessageId();
    const assistantMessage = {
      id: assistantMessageId,
      role: 'assistant' as const,
      content: '',
      timestamp: new Date(),
      status: 'pending' as const,
    };
    setMessages((prev) => [...prev, assistantMessage]);

    // Store the pending message ID for the WebSocket callback
    setPendingMessageId(assistantMessageId);

    try {
      let currentSessionName = state.sessionName;

      if (!currentSessionName) {
        // Start new session
        currentSessionName = chatService.generateSessionName();
        setSessionName(currentSessionName);
        setSessionId(null); // Will be captured from WebSocket

        const request = {
          session_name: currentSessionName,
          prompt,
          async_mode: true,
          ...(state.selectedBlueprint && { agent_blueprint_name: state.selectedBlueprint }),
        };

        await chatService.startSession(request);
      } else {
        // Resume existing session
        await chatService.resumeSession(currentSessionName, {
          prompt,
          async_mode: true,
        });
      }

      // Set status to running - WebSocket will provide the response
      setAgentStatus('starting');

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      // Update assistant message with error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: `Error: ${errorMessage}`, status: 'error' }
            : msg
        )
      );
      showError(errorMessage);
      setAgentStatus('error');
      setIsLoading(false);
      setPendingMessageId(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleNewChat = () => {
    resetChat();
    setInputValue('');
    inputRef.current?.focus();
  };

  // Handle session selection from SessionSelector
  const handleSelectSession = async (session: Session) => {
    try {
      await linkToSession(session);
    } catch (err) {
      showError('Failed to load session');
      console.error(err);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Agent Chat</h2>
          <p className="text-sm text-gray-500">
            Chat with AI agents using the Agent Orchestration Framework
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Connection Status */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
            connected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            {connected ? (
              <Wifi className="w-3 h-3" />
            ) : (
              <WifiOff className="w-3 h-3" />
            )}
            {connected ? 'Connected' : 'Disconnected'}
          </div>

          {/* New Chat Button */}
          <Button
            variant="secondary"
            onClick={handleNewChat}
            disabled={isSessionActive()}
            icon={<RefreshCw className="w-4 h-4" />}
          >
            New Chat
          </Button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {state.messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Bot className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium">Start a conversation</p>
              <p className="text-sm mt-1">
                {state.mode === 'new'
                  ? 'Select an agent and send a message to begin'
                  : 'Select a session from below or start a new chat'}
              </p>
            </div>
          </div>
        ) : (
          <>
            {state.messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-primary-600" />
                  </div>
                )}
                <div
                  className={`max-w-[70%] rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : message.status === 'error'
                      ? 'bg-red-50 text-red-800 border border-red-200'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.status === 'pending' ? (
                    <div className="space-y-2">
                      {/* Tool calls display for pending message */}
                      {state.currentToolCalls.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {state.currentToolCalls.map((tc) => (
                            <ToolCallBadge key={tc.id} tool={tc} />
                          ))}
                        </div>
                      )}
                      {/* Loading indicator */}
                      <div className="flex items-center gap-2">
                        <Spinner size="sm" />
                        <span className="text-sm text-gray-500">
                          {state.currentToolCalls.some(tc => tc.status === 'running')
                            ? 'Working...'
                            : `Agent is ${state.agentStatus || 'starting'}...`}
                        </span>
                      </div>
                    </div>
                  ) : message.role === 'assistant' ? (
                    <div className="space-y-2">
                      {/* Persisted tool calls for completed message */}
                      {message.toolCalls && message.toolCalls.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pb-2 border-b border-gray-200">
                          {message.toolCalls.map((tc) => (
                            <ToolCallBadge key={tc.id} tool={tc} />
                          ))}
                        </div>
                      )}
                      <div className="prose prose-sm max-w-none prose-p:my-2 prose-headings:my-2 prose-ul:my-2 prose-ol:my-2 prose-pre:my-2 prose-pre:bg-gray-800 prose-pre:text-gray-100 prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-th:bg-gray-100 prose-th:px-3 prose-th:py-1.5 prose-td:border prose-td:border-gray-300 prose-td:px-3 prose-td:py-1.5 prose-a:text-primary-600 prose-a:underline">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                      </div>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
                    <User className="w-5 h-5 text-white" />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Bottom Bar with Session Selector and Input */}
      <div className="border-t border-gray-200">
        {/* Session Selector */}
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
          <SessionSelector
            sessions={sessions}
            currentSessionId={state.linkedSessionId || state.sessionId}
            isCurrentSessionActive={isSessionActive()}
            blueprints={blueprints}
            selectedBlueprint={state.selectedBlueprint}
            onSelectBlueprint={setSelectedBlueprint}
            onSelectSession={handleSelectSession}
            onStartNewChat={startNewChat}
            onRefreshBlueprints={loadBlueprints}
            isLoadingBlueprints={isLoadingBlueprints}
            mode={state.mode}
          />
        </div>

        {/* Input Area */}
        <div className="p-4">
          <div className="flex gap-3">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
              disabled={state.isLoading}
              rows={3}
              className="flex-1 px-4 py-3 text-sm border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || state.isLoading || !connected}
              icon={state.isLoading ? <Spinner size="sm" /> : <Send className="w-4 h-4" />}
              className="self-end"
            >
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
