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

// Helper function to convert SessionEvents to ChatMessages
function convertEventsToMessages(events: SessionEvent[]): ChatMessage[] {
  const messages: ChatMessage[] = [];
  const toolCallsMap: Map<number, ToolCall[]> = new Map(); // Map message index to its tool calls

  // First pass: collect all messages and build tool call associations
  let currentAssistantMsgIndex = -1;
  const pendingToolCalls: ToolCall[] = [];

  for (const event of events) {
    if (event.event_type === 'message' && event.role && event.content) {
      // Flush pending tool calls to the previous assistant message
      if (pendingToolCalls.length > 0 && currentAssistantMsgIndex >= 0) {
        toolCallsMap.set(currentAssistantMsgIndex, [...pendingToolCalls]);
        pendingToolCalls.length = 0;
      }

      // Extract text content from the message
      const textContent = event.content
        .filter((block) => block.type === 'text' && block.text)
        .map((block) => block.text)
        .join('\n') || '';

      const msg: ChatMessage = {
        id: `msg-${event.id || event.timestamp}-${Math.random().toString(36).substring(2, 6)}`,
        role: event.role,
        content: textContent,
        timestamp: new Date(event.timestamp),
        status: 'complete',
      };

      messages.push(msg);

      if (event.role === 'assistant') {
        currentAssistantMsgIndex = messages.length - 1;
      }
    } else if (event.event_type === 'post_tool' && event.tool_name) {
      // Collect tool calls - they belong to the next assistant message or current one
      pendingToolCalls.push({
        id: `tool-${event.id || event.timestamp}-${Math.random().toString(36).substring(2, 6)}`,
        name: event.tool_name,
        status: event.error ? 'error' : 'completed',
        timestamp: new Date(event.timestamp),
        input: event.tool_input,
        output: event.tool_output,
        error: event.error,
      });
    }
  }

  // Flush any remaining tool calls to the last assistant message
  if (pendingToolCalls.length > 0 && currentAssistantMsgIndex >= 0) {
    toolCallsMap.set(currentAssistantMsgIndex, [...pendingToolCalls]);
  }

  // Second pass: attach tool calls to messages
  // Tool calls should be attached to the assistant message that comes AFTER them
  // We need to re-process: tool calls belong to the assistant message they precede
  const result: ChatMessage[] = [];
  let accumulatedToolCalls: ToolCall[] = [];

  for (let i = 0; i < events.length; i++) {
    const event = events[i];

    if (event.event_type === 'post_tool' && event.tool_name) {
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
      const textContent = event.content
        .filter((block) => block.type === 'text' && block.text)
        .map((block) => block.text)
        .join('\n') || '';

      const msg: ChatMessage = {
        id: `msg-${event.id || event.timestamp}-${Math.random().toString(36).substring(2, 6)}`,
        role: event.role,
        content: textContent,
        timestamp: new Date(event.timestamp),
        status: 'complete',
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

  // Handle WebSocket messages at context level so they're processed even when Chat tab is not active
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    const currentSessionName = sessionNameRef.current;
    const currentSessionId = sessionIdRef.current;
    const currentLinkedSessionId = linkedSessionIdRef.current;
    const currentPendingMessageId = pendingMessageIdRef.current;
    const currentAgentStatus = agentStatusRef.current;
    const currentIsLoading = isLoadingRef.current;

    // Capture session_id from session_created or session_updated events
    if ((message.type === 'session_created' || message.type === 'session_updated') && message.session) {
      // Match by session_id (preferred) or session_name
      const matchesById = currentSessionId && message.session.session_id === currentSessionId;
      const matchesByLinkedId = currentLinkedSessionId && message.session.session_id === currentLinkedSessionId;
      const matchesByName = currentSessionName && message.session.session_name === currentSessionName;
      const isOurSession = matchesById || matchesByLinkedId || matchesByName;

      if (isOurSession) {
        setSessionId(message.session.session_id);

        // Transition from 'new' to 'linked' mode once session is confirmed
        setMode('linked');

        const backendStatus = message.session.status;

        // Update agent status based on backend session status
        // Note: Callback resume is detected via session_start events, not status changes
        if (backendStatus === 'running') {
          setAgentStatus('running');
        } else if (backendStatus === 'stopping') {
          // Session is being stopped - clear pending state so user can send new messages
          setAgentStatus('stopping');
          if (currentPendingMessageId) {
            // Get current tool calls to attach to the message
            const toolCallsToAttach = [...currentToolCallsRef.current];
            // Mark pending message as complete
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === currentPendingMessageId && msg.status === 'pending'
                  ? {
                      ...msg,
                      content: msg.content || 'Session is being stopped...',
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
        } else if (backendStatus === 'finished' || backendStatus === 'stopped') {
          // Session is no longer running - mark as finished and clear pending state
          setAgentStatus('finished');
          if (currentPendingMessageId) {
            // Get current tool calls to attach to the message
            const toolCallsToAttach = [...currentToolCallsRef.current];
            // Mark pending message as complete
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === currentPendingMessageId && msg.status === 'pending'
                  ? {
                      ...msg,
                      content: msg.content || (backendStatus === 'stopped' ? 'Session stopped' : 'Session ended'),
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
        }
      }
    }

    // Handle message events - this is where we get the agent's response
    if (message.type === 'event' && message.data) {
      const event = message.data;

      // Check if this event is for our session (by sessionId, linkedSessionId, or sessionName)
      const matchesById = currentSessionId && event.session_id === currentSessionId;
      const matchesByLinkedId = currentLinkedSessionId && event.session_id === currentLinkedSessionId;
      const matchesByName = currentSessionName && event.session_name === currentSessionName;
      const isOurSession = matchesById || matchesByLinkedId || matchesByName;

      // If matched by name but we don't have sessionId yet, capture it
      if (matchesByName && !currentSessionId && event.session_id) {
        setSessionId(event.session_id);
      }

      if (!isOurSession) return;

      // Handle session_start event - this indicates session resumed
      if (event.event_type === 'session_start') {
        // Session resumed - update status to running
        // Only set to 'running' if not already in a loading state (user might have just sent a message)
        if (currentAgentStatus !== 'starting' && currentAgentStatus !== 'running') {
          setAgentStatus('running');
        }

        // If there's no pending message and not loading, this is a callback resume (external trigger)
        // For callback resume, fetch updated messages from backend
        if (!currentPendingMessageId && !currentIsLoading) {
          sessionService.getSessionEvents(event.session_id).then((events) => {
            const backendMessages = convertEventsToMessages(events);

            setMessages((prevMessages) => {
              // Check if there are any local messages that need to be preserved
              // (pending messages or recent user messages not in backend)
              const hasPendingMessage = prevMessages.some(m => m.status === 'pending');

              // If there's already a pending message (user initiated), don't replace anything
              // Just let the existing flow handle it
              if (hasPendingMessage) {
                return prevMessages;
              }

              // Pure callback resume - replace with backend messages and add pending
              const newPendingId = `msg-callback-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
              setPendingMessageId(newPendingId);
              return [
                ...backendMessages,
                {
                  id: newPendingId,
                  role: 'assistant' as const,
                  content: '',
                  timestamp: new Date(),
                  status: 'pending' as const,
                },
              ];
            });
            setIsLoading(true);
            setCurrentToolCalls([]);
          });
        }
        return; // Don't process session_start as a regular event
      }

      // Handle assistant messages
      if (event.event_type === 'message' && event.role === 'assistant' && currentPendingMessageId) {
        // Extract text content from the message
        const textContent = event.content
          ?.filter((block: { type: string; text?: string }) => block.type === 'text' && block.text)
          .map((block: { type: string; text?: string }) => block.text)
          .join('\n') || '';

        if (textContent) {
          // Get current tool calls to attach to the message
          const toolCallsToAttach = [...currentToolCallsRef.current];

          // Update the pending message with the response AND attach tool calls
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === currentPendingMessageId
                ? {
                    ...msg,
                    content: textContent,
                    status: 'complete' as const,
                    toolCalls: toolCallsToAttach.length > 0 ? toolCallsToAttach : undefined,
                  }
                : msg
            )
          );
          // Clear current tool calls (they're now attached to the message)
          setCurrentToolCalls([]);
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
        setCurrentToolCalls((prev) => {
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

      // Handle session_stop to mark completion
      if (event.event_type === 'session_stop') {
        // Always update agent status when session stops
        setAgentStatus('finished');
        setIsLoading(false);

        // If we have a pending message, mark it as complete
        if (currentPendingMessageId) {
          // Get current tool calls to attach to the message
          const toolCallsToAttach = [...currentToolCallsRef.current];

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === currentPendingMessageId && msg.status === 'pending'
                ? {
                    ...msg,
                    content: msg.content || 'Session ended',
                    status: 'complete' as const,
                    toolCalls: toolCallsToAttach.length > 0 ? toolCallsToAttach : undefined,
                  }
                : msg
            )
          );
          setCurrentToolCalls([]);
          setPendingMessageId(null);
        }
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
