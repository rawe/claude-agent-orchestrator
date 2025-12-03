import { createContext, useContext, useState, useRef, useCallback, useEffect, ReactNode } from 'react';
import { useWebSocket } from './WebSocketContext';
import type { WebSocketMessage } from '@/types';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'pending' | 'complete' | 'error';
}

interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'error';
  timestamp: Date;
  input?: Record<string, unknown>;
  output?: unknown;
  error?: string;
}

interface ChatState {
  messages: ChatMessage[];
  sessionName: string | null;
  sessionId: string | null;
  selectedBlueprint: string;
  agentStatus: string;
  isLoading: boolean;
  pendingMessageId: string | null;
  toolCalls: ToolCall[];
}

interface ChatContextValue {
  state: ChatState;
  setMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
  setSessionName: (name: string | null) => void;
  setSessionId: (id: string | null) => void;
  setSelectedBlueprint: (blueprint: string) => void;
  setAgentStatus: (status: string) => void;
  setIsLoading: (loading: boolean) => void;
  setPendingMessageId: (id: string | null) => void;
  // Refs for WebSocket callback (avoids stale closures)
  sessionNameRef: React.MutableRefObject<string | null>;
  sessionIdRef: React.MutableRefObject<string | null>;
  pendingMessageIdRef: React.MutableRefObject<string | null>;
  resetChat: () => void;
}

const initialState: ChatState = {
  messages: [],
  sessionName: null,
  sessionId: null,
  selectedBlueprint: '',
  agentStatus: '',
  isLoading: false,
  pendingMessageId: null,
  toolCalls: [],
};

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialState.messages);
  const [sessionName, setSessionNameState] = useState<string | null>(initialState.sessionName);
  const [sessionId, setSessionIdState] = useState<string | null>(initialState.sessionId);
  const [selectedBlueprint, setSelectedBlueprint] = useState<string>(initialState.selectedBlueprint);
  const [agentStatus, setAgentStatus] = useState<string>(initialState.agentStatus);
  const [isLoading, setIsLoading] = useState<boolean>(initialState.isLoading);
  const [pendingMessageId, setPendingMessageIdState] = useState<string | null>(initialState.pendingMessageId);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>(initialState.toolCalls);

  // Refs for WebSocket callbacks
  const sessionNameRef = useRef<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const pendingMessageIdRef = useRef<string | null>(null);

  // Wrapper to keep ref in sync with state
  const setSessionName = (name: string | null) => {
    setSessionNameState(name);
    sessionNameRef.current = name;
  };

  const setSessionId = (id: string | null) => {
    setSessionIdState(id);
    sessionIdRef.current = id;
  };

  const setPendingMessageId = (id: string | null) => {
    setPendingMessageIdState(id);
    pendingMessageIdRef.current = id;
  };

  const resetChat = () => {
    setMessages([]);
    setSessionName(null);
    setSessionId(null);
    setAgentStatus('');
    setIsLoading(false);
    setPendingMessageId(null);
    setToolCalls([]);
    // Don't reset selectedBlueprint - user might want to keep it
  };

  const { subscribe } = useWebSocket();

  // Handle WebSocket messages at context level so they're processed even when Chat tab is not active
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    const currentSessionName = sessionNameRef.current;
    const currentSessionId = sessionIdRef.current;
    const currentPendingMessageId = pendingMessageIdRef.current;

    // Capture session_id from session_created or session_updated events
    if ((message.type === 'session_created' || message.type === 'session_updated') && message.session) {
      if (message.session.session_name === currentSessionName) {
        setSessionId(message.session.session_id);

        // Update status
        if (message.session.status === 'running') {
          setAgentStatus('running');
        } else if (message.session.status === 'finished') {
          setAgentStatus('finished');
        }
      }
    }

    // Handle message events - this is where we get the agent's response
    if (message.type === 'event' && message.data) {
      const event = message.data;

      // Check if this event is for our session
      const isOurSession = currentSessionId
        ? event.session_id === currentSessionId
        : false;

      if (!isOurSession) return;

      // Handle assistant messages
      if (event.event_type === 'message' && event.role === 'assistant' && currentPendingMessageId) {
        // Extract text content from the message
        const textContent = event.content
          ?.filter((block: { type: string; text?: string }) => block.type === 'text' && block.text)
          .map((block: { type: string; text?: string }) => block.text)
          .join('\n') || '';

        if (textContent) {
          // Update the pending message with the response and clear tool calls
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === currentPendingMessageId
                ? { ...msg, content: textContent, status: 'complete' as const }
                : msg
            )
          );
          setToolCalls([]);
          setAgentStatus('finished');
          setIsLoading(false);
          setPendingMessageId(null);
        }
      }

      // Handle post_tool events - tool completed
      if (event.event_type === 'post_tool' && event.tool_name) {
        const toolName = event.tool_name;
        const toolInput = event.tool_input;
        const toolOutput = event.tool_output;
        const toolError = event.error;
        const now = Date.now();
        setToolCalls((prev) => {
          // Deduplicate: check if same tool was added in last 500ms
          const recentDuplicate = prev.some(
            (tc) => tc.name === toolName && now - tc.timestamp.getTime() < 500
          );
          if (recentDuplicate) return prev;

          return [
            ...prev,
            {
              id: `tool-${now}-${Math.random().toString(36).substring(2, 6)}`,
              name: toolName,
              status: toolError ? 'error' : 'completed',
              timestamp: new Date(now),
              input: toolInput,
              output: toolOutput,
              error: toolError,
            },
          ];
        });
      }

      // Also handle session_stop to mark completion if no message was received
      if (event.event_type === 'session_stop' && currentPendingMessageId) {
        // Session ended - if we still have a pending message, mark it as complete
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === currentPendingMessageId && msg.status === 'pending'
              ? { ...msg, content: msg.content || 'Session ended', status: 'complete' as const }
              : msg
          )
        );
        setToolCalls([]);
        setAgentStatus('finished');
        setIsLoading(false);
        setPendingMessageId(null);
      }
    }
  }, []);

  // Subscribe to WebSocket at context level
  useEffect(() => {
    const unsubscribe = subscribe(handleWebSocketMessage);
    return () => unsubscribe();
  }, [subscribe, handleWebSocketMessage]);

  const state: ChatState = {
    messages,
    sessionName,
    sessionId,
    selectedBlueprint,
    agentStatus,
    isLoading,
    pendingMessageId,
    toolCalls,
  };

  return (
    <ChatContext.Provider
      value={{
        state,
        setMessages,
        setSessionName,
        setSessionId,
        setSelectedBlueprint,
        setAgentStatus,
        setIsLoading,
        setPendingMessageId,
        sessionNameRef,
        sessionIdRef,
        pendingMessageIdRef,
        resetChat,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}
