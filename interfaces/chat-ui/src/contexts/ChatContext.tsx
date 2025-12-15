import { createContext, useContext, useCallback, useEffect, useRef, useReducer, type ReactNode } from 'react';
import { useWebSocket } from './WebSocketContext';
import { chatService } from '../services/api';
import type {
  ChatMessage,
  ToolCall,
  AgentStatus,
  WebSocketMessage,
  SessionEvent,
  ContentBlock,
} from '../types';

// Helper: Generate unique ID
const generateId = () => `${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;

// Helper: Extract text content from content blocks
function extractTextContent(content: ContentBlock[] | undefined): string {
  if (!content) return '';
  return content
    .filter((block) => block.type === 'text' && block.text)
    .map((block) => block.text)
    .join('\n') || '';
}

// Helper: Check if message already exists (deduplication for StrictMode double-mount)
// Matches by role, content, and timestamp proximity (within 2 seconds)
function messageExists(
  messages: ChatMessage[],
  role: 'user' | 'assistant',
  content: string,
  timestamp: Date
): boolean {
  const eventTime = timestamp.getTime();
  return messages.some((m) => {
    if (m.role !== role) return false;
    if (m.content !== content) return false;
    // Within 2 seconds = same message
    return Math.abs(m.timestamp.getTime() - eventTime) < 2000;
  });
}

// State interface
interface ChatState {
  messages: ChatMessage[];
  sessionName: string | null;
  sessionId: string | null;
  agentStatus: AgentStatus;
  isLoading: boolean;
  pendingMessageId: string | null;
  currentToolCalls: ToolCall[];
  error: string | null;
}

// Actions
type ChatAction =
  | { type: 'ADD_USER_MESSAGE'; message: ChatMessage }
  | { type: 'ADD_PENDING_ASSISTANT_MESSAGE'; id: string }
  | { type: 'UPDATE_ASSISTANT_MESSAGE'; content: string }
  | { type: 'COMPLETE_ASSISTANT_MESSAGE' }
  | { type: 'ADD_ASSISTANT_MESSAGE'; message: ChatMessage }
  | { type: 'ADD_TOOL_CALL'; tool: ToolCall }
  | { type: 'UPDATE_TOOL_CALL'; id: string; updates: Partial<ToolCall> }
  | { type: 'SET_SESSION'; sessionName: string; sessionId: string }
  | { type: 'SET_SESSION_ID'; sessionId: string }
  | { type: 'SET_AGENT_STATUS'; status: AgentStatus }
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'RESET_CHAT' };

// Initial state
const initialState: ChatState = {
  messages: [],
  sessionName: null,
  sessionId: null,
  agentStatus: 'idle',
  isLoading: false,
  pendingMessageId: null,
  currentToolCalls: [],
  error: null,
};

// Reducer
function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'ADD_USER_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.message],
      };

    case 'ADD_PENDING_ASSISTANT_MESSAGE':
      return {
        ...state,
        pendingMessageId: action.id,
        currentToolCalls: [],
        messages: [
          ...state.messages,
          {
            id: action.id,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            status: 'pending',
          },
        ],
      };

    case 'UPDATE_ASSISTANT_MESSAGE':
      return {
        ...state,
        messages: state.messages.map((msg) =>
          msg.id === state.pendingMessageId
            ? { ...msg, content: action.content }
            : msg
        ),
      };

    case 'COMPLETE_ASSISTANT_MESSAGE':
      return {
        ...state,
        messages: state.messages.map((msg) =>
          msg.id === state.pendingMessageId
            ? { ...msg, status: 'complete', toolCalls: [...state.currentToolCalls] }
            : msg
        ),
        pendingMessageId: null,
        currentToolCalls: [],
      };

    case 'ADD_ASSISTANT_MESSAGE':
      // Add a complete assistant message (for messages arriving after session_stop)
      // Deduplication: skip if message already exists (StrictMode safeguard)
      if (messageExists(
        state.messages,
        action.message.role,
        action.message.content,
        action.message.timestamp
      )) {
        return state;
      }
      return {
        ...state,
        messages: [...state.messages, action.message],
      };

    case 'ADD_TOOL_CALL':
      // Check for duplicate (same name within 500ms)
      const isDuplicate = state.currentToolCalls.some(
        (tc) =>
          tc.name === action.tool.name &&
          Math.abs(tc.timestamp.getTime() - action.tool.timestamp.getTime()) < 500
      );
      if (isDuplicate) return state;
      return {
        ...state,
        currentToolCalls: [...state.currentToolCalls, action.tool],
      };

    case 'UPDATE_TOOL_CALL':
      return {
        ...state,
        currentToolCalls: state.currentToolCalls.map((tc) =>
          tc.id === action.id ? { ...tc, ...action.updates } : tc
        ),
      };

    case 'SET_SESSION':
      return {
        ...state,
        sessionName: action.sessionName,
        sessionId: action.sessionId,
      };

    case 'SET_SESSION_ID':
      return {
        ...state,
        sessionId: action.sessionId,
      };

    case 'SET_AGENT_STATUS':
      return {
        ...state,
        agentStatus: action.status,
        isLoading: action.status === 'starting' || action.status === 'running',
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.loading,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.error,
        agentStatus: action.error ? 'error' : state.agentStatus,
        isLoading: false,
      };

    case 'RESET_CHAT':
      return initialState;

    default:
      return state;
  }
}

// Context interface
interface ChatContextValue {
  state: ChatState;
  sendMessage: (prompt: string) => Promise<void>;
  stopAgent: () => Promise<void>;
  resetChat: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const { subscribe } = useWebSocket();

  // Refs to avoid stale closures in WebSocket handler
  // These are updated SYNCHRONOUSLY to prevent race conditions in StrictMode
  const sessionNameRef = useRef<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const pendingMessageIdRef = useRef<string | null>(null);

  // Wrapper functions that update refs synchronously with dispatch
  // This prevents StrictMode double-mount issues where refs lag behind state
  const setSession = useCallback((sessionName: string, sessionId: string) => {
    sessionNameRef.current = sessionName;
    sessionIdRef.current = sessionId;
    dispatch({ type: 'SET_SESSION', sessionName, sessionId });
  }, []);

  const setSessionId = useCallback((sessionId: string) => {
    sessionIdRef.current = sessionId;
    dispatch({ type: 'SET_SESSION_ID', sessionId });
  }, []);

  const addPendingAssistantMessage = useCallback((id: string) => {
    pendingMessageIdRef.current = id;
    dispatch({ type: 'ADD_PENDING_ASSISTANT_MESSAGE', id });
  }, []);

  const completeAssistantMessage = useCallback(() => {
    pendingMessageIdRef.current = null;
    dispatch({ type: 'COMPLETE_ASSISTANT_MESSAGE' });
  }, []);

  const resetChatState = useCallback(() => {
    sessionNameRef.current = null;
    sessionIdRef.current = null;
    pendingMessageIdRef.current = null;
    dispatch({ type: 'RESET_CHAT' });
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    // Check if message belongs to our session
    const isOurSession = (msg: WebSocketMessage): boolean => {
      if ('session' in msg && msg.session) {
        return (
          msg.session.session_id === sessionIdRef.current ||
          msg.session.session_name === sessionNameRef.current
        );
      }
      if ('data' in msg && msg.data) {
        return (
          msg.data.session_id === sessionIdRef.current ||
          msg.data.session_name === sessionNameRef.current
        );
      }
      return false;
    };

    if (!isOurSession(message)) return;

    // Handle session lifecycle
    if (message.type === 'session_created' || message.type === 'session_updated') {
      const session = message.session;
      if (session.session_id && !sessionIdRef.current) {
        setSessionId(session.session_id);
      }

      // Update status based on session status
      const statusMap: Record<string, AgentStatus> = {
        starting: 'starting',
        running: 'running',
        stopping: 'stopping',
        stopped: 'finished',
        finished: 'finished',
      };
      if (session.status && statusMap[session.status]) {
        dispatch({ type: 'SET_AGENT_STATUS', status: statusMap[session.status] });
      }
    }

    // Handle events
    if (message.type === 'event' && message.data) {
      const event: SessionEvent = message.data;

      switch (event.event_type) {
        case 'session_start':
          dispatch({ type: 'SET_AGENT_STATUS', status: 'running' });
          break;

        case 'session_stop':
          dispatch({ type: 'SET_AGENT_STATUS', status: 'finished' });
          completeAssistantMessage();
          break;

        case 'pre_tool':
          // Tool is starting - add as running
          if (event.tool_name) {
            dispatch({
              type: 'ADD_TOOL_CALL',
              tool: {
                id: generateId(),
                name: event.tool_name,
                status: 'running',
                timestamp: new Date(event.timestamp),
                input: event.tool_input,
              },
            });
          }
          break;

        case 'post_tool':
          // Tool completed - update or add
          if (event.tool_name) {
            const toolId = generateId();
            dispatch({
              type: 'ADD_TOOL_CALL',
              tool: {
                id: toolId,
                name: event.tool_name,
                status: event.error ? 'error' : 'completed',
                timestamp: new Date(event.timestamp),
                input: event.tool_input,
                output: event.tool_output,
                error: event.error,
              },
            });
          }
          break;

        case 'message':
          // Only show assistant messages
          if (event.role === 'assistant' && event.content) {
            const textContent = extractTextContent(event.content);
            if (textContent) {
              if (pendingMessageIdRef.current) {
                // Update existing pending message
                dispatch({ type: 'UPDATE_ASSISTANT_MESSAGE', content: textContent });
              } else {
                // No pending message - agent sent additional response after session_stop
                // Create a new complete message
                dispatch({
                  type: 'ADD_ASSISTANT_MESSAGE',
                  message: {
                    id: generateId(),
                    role: 'assistant',
                    content: textContent,
                    timestamp: new Date(event.timestamp),
                    status: 'complete',
                  },
                });
              }
            }
          }
          break;
      }
    }
  }, [setSessionId, completeAssistantMessage]);

  // Subscribe to WebSocket - use ref pattern to avoid re-subscription
  const handlerRef = useRef(handleWebSocketMessage);
  handlerRef.current = handleWebSocketMessage;

  useEffect(() => {
    const stableHandler = (msg: WebSocketMessage) => handlerRef.current(msg);
    const unsubscribe = subscribe(stableHandler);
    return () => unsubscribe();
  }, [subscribe]);

  // Send message
  const sendMessage = useCallback(async (prompt: string) => {
    if (!prompt.trim()) return;

    dispatch({ type: 'SET_ERROR', error: null });

    // Add user message
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: prompt,
      timestamp: new Date(),
      status: 'complete',
    };
    dispatch({ type: 'ADD_USER_MESSAGE', message: userMessage });

    // Add pending assistant message
    const assistantMessageId = generateId();
    addPendingAssistantMessage(assistantMessageId);

    // Set status to starting
    dispatch({ type: 'SET_AGENT_STATUS', status: 'starting' });

    try {
      if (!state.sessionName) {
        // First message: start new session
        const { sessionName } = await chatService.startSession(prompt);
        setSession(sessionName, '');
      } else {
        // Session exists (status=finished means idle, ready to resume)
        await chatService.resumeSession(state.sessionName, prompt);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      dispatch({ type: 'SET_ERROR', error: errorMessage });
      completeAssistantMessage();
    }
  }, [state.sessionName, addPendingAssistantMessage, setSession, completeAssistantMessage]);

  // Stop agent
  const stopAgent = useCallback(async () => {
    if (!state.sessionId) return;

    dispatch({ type: 'SET_AGENT_STATUS', status: 'stopping' });

    try {
      await chatService.stopSession(state.sessionId);
    } catch (error) {
      console.error('Failed to stop session:', error);
    }
  }, [state.sessionId]);

  // Reset chat
  const resetChat = useCallback(() => {
    resetChatState();
  }, [resetChatState]);

  return (
    <ChatContext.Provider value={{ state, sendMessage, stopAgent, resetChat }}>
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
