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
  const [agentStatus, setAgentStatus] = useState<string>(initialState.agentStatus);
  const [isLoading, setIsLoading] = useState<boolean>(initialState.isLoading);
  const [pendingMessageId, setPendingMessageIdState] = useState<string | null>(initialState.pendingMessageId);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>(initialState.currentToolCalls);

  // Refs for WebSocket callbacks
  const sessionNameRef = useRef<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const pendingMessageIdRef = useRef<string | null>(null);
  const linkedSessionIdRef = useRef<string | null>(null);

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

  const setLinkedSessionId = (id: string | null) => {
    setLinkedSessionIdState(id);
    linkedSessionIdRef.current = id;
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
    setAgentStatus(session.status === 'running' ? 'running' : 'finished');
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

    // Capture session_id from session_created or session_updated events
    if ((message.type === 'session_created' || message.type === 'session_updated') && message.session) {
      if (message.session.session_name === currentSessionName) {
        setSessionId(message.session.session_id);

        // Transition from 'new' to 'linked' mode once session is confirmed
        setMode('linked');

        // Update status - but only set 'running', not 'finished'
        // The 'finished' status should only be set when we receive the actual response,
        // otherwise we get a race condition where "Agent is finished" shows while still waiting
        if (message.session.status === 'running') {
          // Check if session was previously finished - this indicates a callback resume
          const wasFinished = agentStatus === 'finished';

          setAgentStatus('running');

          // If session was finished and is now running again, this is a callback resume
          // Add a pending assistant message to show the agent is responding
          if (wasFinished && !currentPendingMessageId) {
            const newPendingId = `msg-callback-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
            setMessages((prev) => [
              ...prev,
              {
                id: newPendingId,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                status: 'pending',
              },
            ]);
            setPendingMessageId(newPendingId);
            setIsLoading(true);
            setCurrentToolCalls([]);
          }
        }
        // Note: 'finished' status is set when assistant message arrives (line ~332)
      }
    }

    // Handle message events - this is where we get the agent's response
    if (message.type === 'event' && message.data) {
      const event = message.data;

      // Check if this event is for our session (either by sessionId or linkedSessionId)
      const isOurSession = currentSessionId
        ? event.session_id === currentSessionId
        : currentLinkedSessionId
        ? event.session_id === currentLinkedSessionId
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

      // Also handle session_stop to mark completion if no message was received
      if (event.event_type === 'session_stop' && currentPendingMessageId) {
        // Get current tool calls to attach to the message
        const toolCallsToAttach = [...currentToolCallsRef.current];

        // Session ended - if we still have a pending message, mark it as complete
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
