import { createContext, useContext, useState, useRef, useCallback, useEffect, ReactNode } from 'react';
import { useWebSocket } from './WebSocketContext';
import { sessionService } from '@/services';
import type { WebSocketMessage, SessionEvent, Session } from '@/types';

export interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'error';
  timestamp: Date;
  input?: Record<string, unknown>;
  output?: unknown;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'pending' | 'complete' | 'error';
  toolCalls?: ToolCall[];  // Tool calls associated with this message
}

type ChatMode = 'new' | 'linked';

interface ChatState {
  messages: ChatMessage[];
  sessionName: string | null;
  sessionId: string | null;
  linkedSessionId: string | null;  // When linked to an existing session
  mode: ChatMode;
  selectedBlueprint: string;
  agentStatus: string;
  isLoading: boolean;
  pendingMessageId: string | null;
  currentToolCalls: ToolCall[];  // Tool calls for the current pending message
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
  linkedSessionIdRef: React.MutableRefObject<string | null>;
  resetChat: () => void;
  // Session linking
  linkToSession: (session: Session) => Promise<void>;
  startNewChat: () => void;
  isSessionActive: () => boolean;
}

const initialState: ChatState = {
  messages: [],
  sessionName: null,
  sessionId: null,
  linkedSessionId: null,
  mode: 'new',
  selectedBlueprint: '',
  agentStatus: '',
  isLoading: false,
  pendingMessageId: null,
  currentToolCalls: [],
};

const ChatContext = createContext<ChatContextValue | null>(null);

// ============================================================================
// HELPER FUNCTIONS FOR MESSAGE HANDLING
// ============================================================================

/**
 * Extract text content from event content blocks
 */
function extractTextContent(content: Array<{ type: string; text?: string }> | undefined): string {
  if (!content) return '';
  return content
    .filter((block) => block.type === 'text' && block.text)
    .map((block) => block.text)
    .join('\n') || '';
}

/**
 * Create a ChatMessage from a SessionEvent
 */
function createMessageFromEvent(event: SessionEvent): ChatMessage {
  return {
    id: `msg-${event.id || event.timestamp}-${Math.random().toString(36).substring(2, 6)}`,
    role: event.role as 'user' | 'assistant',
    content: extractTextContent(event.content),
    timestamp: new Date(event.timestamp),
    status: 'complete',
  };
}

/**
 * Check if a message already exists in the messages array (deduplication)
 * Matches by role, content, and timestamp proximity (within 2 seconds)
 */
function messageExists(messages: ChatMessage[], event: SessionEvent): boolean {
  const eventContent = extractTextContent(event.content);
  const eventTime = new Date(event.timestamp).getTime();

  return messages.some(m => {
    if (m.role !== event.role) return false;
    if (m.content !== eventContent) return false;
    // Within 2 seconds = same message
    return Math.abs(m.timestamp.getTime() - eventTime) < 2000;
  });
}

/**
 * Convert SessionEvents to ChatMessages (used when loading session history)
 * Handles tool call association with assistant messages
 */
function convertEventsToMessages(events: SessionEvent[]): ChatMessage[] {
  const result: ChatMessage[] = [];
  let accumulatedToolCalls: ToolCall[] = [];

  for (const event of events) {
    if (event.event_type === 'post_tool' && event.tool_name) {
      // Accumulate tool calls - they'll be attached to the next assistant message
      accumulatedToolCalls.push({
        id: `tool-${event.id || event.timestamp}-${Math.random().toString(36).substring(2, 6)}`,
        name: event.tool_name,
        status: event.error ? 'error' : 'completed',
        timestamp: new Date(event.timestamp),
        input: event.tool_input,
        output: event.tool_output,
        error: event.error,
      });
    } else if (event.event_type === 'message' && event.role && event.content) {
      const textContent = extractTextContent(event.content);

      const msg: ChatMessage = {
        id: `msg-${event.id || event.timestamp}-${Math.random().toString(36).substring(2, 6)}`,
        role: event.role,
        content: textContent,
        timestamp: new Date(event.timestamp),
        status: 'complete',
        // Attach accumulated tool calls to assistant messages
        toolCalls: event.role === 'assistant' && accumulatedToolCalls.length > 0
          ? [...accumulatedToolCalls]
          : undefined,
      };

      result.push(msg);

      // Clear accumulated tool calls after attaching to assistant message
      if (event.role === 'assistant') {
        accumulatedToolCalls = [];
      }
    }
  }

  return result;
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialState.messages);
  const [sessionName, setSessionNameState] = useState<string | null>(initialState.sessionName);
  const [sessionId, setSessionIdState] = useState<string | null>(initialState.sessionId);
  const [linkedSessionId, setLinkedSessionIdState] = useState<string | null>(initialState.linkedSessionId);
  const [mode, setMode] = useState<ChatMode>(initialState.mode);
  const [selectedBlueprint, setSelectedBlueprint] = useState<string>(initialState.selectedBlueprint);
  const [agentStatus, setAgentStatusState] = useState<string>(initialState.agentStatus);
  const [isLoading, setIsLoadingState] = useState<boolean>(initialState.isLoading);
  const [pendingMessageId, setPendingMessageIdState] = useState<string | null>(initialState.pendingMessageId);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>(initialState.currentToolCalls);

  // Refs for WebSocket callbacks - these must be updated synchronously to avoid race conditions
  const sessionNameRef = useRef<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const pendingMessageIdRef = useRef<string | null>(null);
  const linkedSessionIdRef = useRef<string | null>(null);
  const agentStatusRef = useRef<string>(initialState.agentStatus);
  const isLoadingRef = useRef<boolean>(initialState.isLoading);

  // Wrappers to keep refs in sync with state (synchronous updates for WebSocket handlers)
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

  const setLinkedSessionId = (id: string | null) => {
    setLinkedSessionIdState(id);
    linkedSessionIdRef.current = id;
  };

  const setAgentStatus = (status: string) => {
    setAgentStatusState(status);
    agentStatusRef.current = status;
  };

  const setIsLoading = (loading: boolean) => {
    setIsLoadingState(loading);
    isLoadingRef.current = loading;
  };

  const resetChat = () => {
    setMessages([]);
    setSessionName(null);
    setSessionId(null);
    setLinkedSessionId(null);
    setMode('new');
    setAgentStatus('');
    setIsLoading(false);
    setPendingMessageId(null);
    setCurrentToolCalls([]);
    // Don't reset selectedBlueprint - user might want to keep it
  };

  // Start a new chat (unlink from any session)
  const startNewChat = useCallback(() => {
    resetChat();
  }, []);

  // Link to an existing session
  const linkToSession = useCallback(async (session: Session) => {
    // Fetch events for this session
    const events = await sessionService.getSessionEvents(session.session_id);

    // Convert events to messages
    const convertedMessages = convertEventsToMessages(events);

    // Update state
    setMessages(convertedMessages);
    setSessionId(session.session_id);
    setLinkedSessionId(session.session_id);
    setSessionName(session.session_name || null);
    setMode('linked');
    // Map session status to agent status
    const statusMap: Record<string, string> = {
      running: 'running',
      stopping: 'stopping',
      stopped: 'finished',
      finished: 'finished',
    };
    setAgentStatus(statusMap[session.status] || 'finished');
    setIsLoading(false);
    setPendingMessageId(null);
    setCurrentToolCalls([]);
  }, []);

  // Check if current session is active (running)
  const isSessionActive = useCallback(() => {
    return isLoading || agentStatus === 'running' || agentStatus === 'starting';
  }, [isLoading, agentStatus]);

  const { subscribe } = useWebSocket();

  // Ref to track current tool calls for the pending message (needed for WebSocket callback)
  const currentToolCallsRef = useRef<ToolCall[]>([]);

  // Keep ref in sync
  useEffect(() => {
    currentToolCallsRef.current = currentToolCalls;
  }, [currentToolCalls]);

  // ============================================================================
  // WEBSOCKET MESSAGE HANDLER
  // ============================================================================
  //
  // This handler processes all WebSocket events for the chat.
  //
  // MESSAGE FLOW:
  // 1. session_created/session_updated → Update session state
  // 2. session_start → Handle session resume (callback or manual)
  // 3. message (user OR assistant) → Add/update messages
  // 4. post_tool → Track tool calls
  // 5. session_stop → Mark session as finished
  //
  // KEY DESIGN: Both user AND assistant messages are processed uniformly.
  // This handles callback mode where user messages come from the backend.
  // ============================================================================

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    // Get current values from refs (avoids stale closures)
    const currentSessionName = sessionNameRef.current;
    const currentSessionId = sessionIdRef.current;
    const currentLinkedSessionId = linkedSessionIdRef.current;
    const currentPendingMessageId = pendingMessageIdRef.current;
    const currentAgentStatus = agentStatusRef.current;
    const currentIsLoading = isLoadingRef.current;

    // -------------------------------------------------------------------------
    // HELPER: Check if this event/session belongs to our chat
    // -------------------------------------------------------------------------
    const isOurSessionById = (id: string) =>
      (currentSessionId && id === currentSessionId) ||
      (currentLinkedSessionId && id === currentLinkedSessionId);

    const isOurSessionByName = (name: string) =>
      currentSessionName && name === currentSessionName;

    // -------------------------------------------------------------------------
    // HANDLER: Session state changes (session_created / session_updated)
    // -------------------------------------------------------------------------
    if ((message.type === 'session_created' || message.type === 'session_updated') && message.session) {
      const session = message.session;
      const isOurSession =
        isOurSessionById(session.session_id) ||
        isOurSessionByName(session.session_name || '');

      if (!isOurSession) return;

      // Capture session_id and transition to linked mode
      setSessionId(session.session_id);
      setMode('linked');

      // Handle session status changes
      const backendStatus = session.status;

      if (backendStatus === 'running') {
        setAgentStatus('running');
      } else if (backendStatus === 'stopping') {
        handleSessionStopping();
      } else if (backendStatus === 'finished' || backendStatus === 'stopped') {
        handleSessionFinished();
      }
      return;
    }

    // -------------------------------------------------------------------------
    // HANDLER: Event messages (message, tool, lifecycle events)
    // -------------------------------------------------------------------------
    if (message.type === 'event' && message.data) {
      const event = message.data;

      // Check if this event is for our session
      const isOurSession =
        isOurSessionById(event.session_id) ||
        isOurSessionByName(event.session_name || '');

      if (!isOurSession) return;

      // Capture session_id if we matched by name
      if (!currentSessionId && event.session_id) {
        setSessionId(event.session_id);
      }

      // --- SESSION RESUME (session_start) ---
      // This fires when a session is resumed (e.g., callback mode)
      // We set up pending state but DON'T return early - subsequent events need processing
      if (event.event_type === 'session_start') {
        handleSessionResume(currentAgentStatus, currentPendingMessageId, currentIsLoading);
        // NO RETURN - let subsequent message events be processed
      }

      // --- SESSION STOP ---
      if (event.event_type === 'session_stop') {
        handleSessionStop(currentPendingMessageId);
        return;
      }

      // --- MESSAGE EVENTS (user AND assistant) ---
      // This is the unified handler for both roles
      // Read pendingMessageId fresh from ref (not captured value) to get latest state
      if (event.event_type === 'message' && event.role && event.content) {
        handleMessageEvent(event, pendingMessageIdRef.current);
        return;
      }

      // --- TOOL EVENTS ---
      if (event.event_type === 'post_tool' && event.tool_name) {
        handleToolEvent(event);
        return;
      }
    }
  }, []);

  // -------------------------------------------------------------------------
  // HANDLER FUNCTIONS (separated for clarity)
  // -------------------------------------------------------------------------

  /**
   * Handle session being stopped (user clicked stop)
   * Note: Only updates status. Pending message will be completed by session_stop event.
   */
  function handleSessionStopping() {
    setAgentStatus('stopping');
    // DON'T clear pending message here - let session_stop event handle it
  }

  /**
   * Handle session status changed to finished or stopped
   *
   * IMPORTANT: "finished" means agent's turn ended, NOT "session is done forever".
   * All sessions are resumable. Only update status to enable user input.
   * Let message events and session_stop handle pending message completion.
   */
  function handleSessionFinished() {
    setAgentStatus('finished');
    // DON'T clear pending message here!
    // - Message events will update it with actual content
    // - session_stop event will complete it if still pending
  }

  /**
   * Handle session resume (callback mode or manual resume)
   * Sets up pending assistant message for incoming response
   */
  function handleSessionResume(
    currentAgentStatus: string,
    currentPendingMessageId: string | null,
    currentIsLoading: boolean
  ) {
    // Update status to running if not already in a loading state
    if (currentAgentStatus !== 'starting' && currentAgentStatus !== 'running') {
      setAgentStatus('running');
    }

    // If this is a callback resume (no pending message, not loading),
    // set up state for incoming messages
    if (!currentPendingMessageId && !currentIsLoading) {
      const newPendingId = `msg-callback-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
      setPendingMessageId(newPendingId);
      setIsLoading(true);
      setCurrentToolCalls([]);

      // Add pending assistant message placeholder
      setMessages(prev => [...prev, {
        id: newPendingId,
        role: 'assistant' as const,
        content: '',
        timestamp: new Date(),
        status: 'pending' as const,
      }]);
    }
  }

  /**
   * Handle session stop event
   */
  function handleSessionStop(pendingMessageId: string | null) {
    setAgentStatus('finished');
    setIsLoading(false);

    if (pendingMessageId) {
      completePendingMessage(pendingMessageId, 'Session ended');
    }
  }

  /**
   * UNIFIED MESSAGE HANDLER - processes both user AND assistant messages
   * This is the key fix: callback user messages are now handled here
   */
  function handleMessageEvent(event: SessionEvent, pendingMessageId: string | null) {
    const textContent = extractTextContent(event.content);
    if (!textContent) return;

    // --- USER MESSAGE ---
    // User messages from WebSocket are typically callback results
    // They should be inserted BEFORE the pending assistant message
    if (event.role === 'user') {
      setMessages(prev => {
        // Deduplication: skip if message already exists
        if (messageExists(prev, event)) return prev;

        const newMsg = createMessageFromEvent(event);

        // Find pending assistant message and insert user message before it
        const pendingIdx = prev.findIndex(m => m.status === 'pending');
        if (pendingIdx >= 0) {
          return [...prev.slice(0, pendingIdx), newMsg, ...prev.slice(pendingIdx)];
        }
        return [...prev, newMsg];
      });
      return;
    }

    // --- ASSISTANT MESSAGE ---
    if (event.role === 'assistant') {
      if (pendingMessageId) {
        // Update the pending message with the response
        const toolCallsToAttach = [...currentToolCallsRef.current];
        setMessages(prev => prev.map(msg =>
          msg.id === pendingMessageId
            ? {
                ...msg,
                content: textContent,
                status: 'complete' as const,
                toolCalls: toolCallsToAttach.length > 0 ? toolCallsToAttach : undefined,
              }
            : msg
        ));
        setCurrentToolCalls([]);
        setAgentStatus('finished');
        setIsLoading(false);
        setPendingMessageId(null);
      } else {
        // No pending message - add as new complete message
        setMessages(prev => {
          if (messageExists(prev, event)) return prev;
          return [...prev, createMessageFromEvent(event)];
        });
      }
    }
  }

  /**
   * Handle tool call events
   */
  function handleToolEvent(event: SessionEvent) {
    const toolName = event.tool_name!;
    const toolInput = event.tool_input;
    const toolOutput = event.tool_output;
    const toolError = event.error;
    const now = Date.now();

    setCurrentToolCalls(prev => {
      // Deduplicate: check if same tool was added in last 500ms
      const recentDuplicate = prev.some(
        tc => tc.name === toolName && now - tc.timestamp.getTime() < 500
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

  /**
   * Complete a pending message with content
   */
  function completePendingMessage(pendingMessageId: string, fallbackContent: string) {
    const toolCallsToAttach = [...currentToolCallsRef.current];
    setMessages(prev =>
      prev.map(msg =>
        msg.id === pendingMessageId && msg.status === 'pending'
          ? {
              ...msg,
              content: msg.content || fallbackContent,
              status: 'complete' as const,
              toolCalls: toolCallsToAttach.length > 0 ? toolCallsToAttach : undefined,
            }
          : msg
      )
    );
    setCurrentToolCalls([]);
    setIsLoading(false);
    setPendingMessageId(null);
  }

  // Subscribe to WebSocket at context level
  // Use a ref to ensure stable handler reference across StrictMode's double-effect behavior
  const handleWebSocketMessageRef = useRef(handleWebSocketMessage);
  handleWebSocketMessageRef.current = handleWebSocketMessage;

  useEffect(() => {
    // Create a stable wrapper that delegates to the ref
    // This ensures we have ONE subscription even if effect runs twice
    const stableHandler = (msg: WebSocketMessage) => handleWebSocketMessageRef.current(msg);
    const unsubscribe = subscribe(stableHandler);
    return () => unsubscribe();
  }, [subscribe]);

  const state: ChatState = {
    messages,
    sessionName,
    sessionId,
    linkedSessionId,
    mode,
    selectedBlueprint,
    agentStatus,
    isLoading,
    pendingMessageId,
    currentToolCalls,
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
        linkedSessionIdRef,
        resetChat,
        linkToSession,
        startNewChat,
        isSessionActive,
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
