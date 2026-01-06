import { createContext, useContext, useCallback, useEffect, useRef, useReducer, type ReactNode } from 'react';
import { useSSE } from './SSEContext';
import { chatService } from '../services/api';
import type {
  ChatMessage,
  ToolCall,
  AgentStatus,
  StreamMessage,
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
  role: 'user' | 'assistant' | 'system',
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
  sessionId: string | null;
  agentStatus: AgentStatus;
  isLoading: boolean;
  pendingMessageId: string | null;
  currentToolCalls: ToolCall[];
  error: string | null;
  isInitialized: boolean;
}

// Actions
type ChatAction =
  | { type: 'ADD_USER_MESSAGE'; message: ChatMessage }
  | { type: 'ADD_PENDING_ASSISTANT_MESSAGE'; id: string }
  | { type: 'UPDATE_ASSISTANT_MESSAGE'; content: string }
  | { type: 'COMPLETE_ASSISTANT_MESSAGE' }
  | { type: 'ADD_ASSISTANT_MESSAGE'; message: ChatMessage }
  | { type: 'ADD_SYSTEM_MESSAGE'; message: ChatMessage }
  | { type: 'REMOVE_SYSTEM_MESSAGES' }
  | { type: 'ADD_TOOL_CALL'; tool: ToolCall }
  | { type: 'UPDATE_TOOL_CALL'; id: string; updates: Partial<ToolCall> }
  | { type: 'SET_SESSION_ID'; sessionId: string }
  | { type: 'SET_AGENT_STATUS'; status: AgentStatus }
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'SET_INITIALIZED'; initialized: boolean }
  | { type: 'RESET_CHAT' };

// Initial state
const initialState: ChatState = {
  messages: [],
  sessionId: null,
  agentStatus: 'idle',
  isLoading: false,
  pendingMessageId: null,
  currentToolCalls: [],
  error: null,
  isInitialized: false,
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
      // Add a complete assistant message (for messages arriving after run_completed)
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

    case 'ADD_SYSTEM_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.message],
      };

    case 'REMOVE_SYSTEM_MESSAGES':
      return {
        ...state,
        messages: state.messages.filter((msg) => msg.role !== 'system'),
      };

    case 'SET_INITIALIZED':
      return {
        ...state,
        isInitialized: action.initialized,
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
  initializeChat: () => Promise<void>;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const { subscribe } = useSSE();

  // Refs to avoid stale closures in SSE handler
  // These are updated SYNCHRONOUSLY to prevent race conditions in StrictMode
  const sessionIdRef = useRef<string | null>(null);
  const pendingMessageIdRef = useRef<string | null>(null);

  // Wrapper functions that update refs synchronously with dispatch
  // This prevents StrictMode double-mount issues where refs lag behind state
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
    sessionIdRef.current = null;
    pendingMessageIdRef.current = null;
    dispatch({ type: 'RESET_CHAT' });
  }, []);

  // Initialize chat - sends hidden "start" prompt to begin session
  const initializeChat = useCallback(async () => {
    dispatch({ type: 'SET_ERROR', error: null });
    dispatch({ type: 'SET_INITIALIZED', initialized: true });

    // Add system message "Session initializing..."
    const systemMessage: ChatMessage = {
      id: generateId(),
      role: 'system',
      content: 'Session initializing...',
      timestamp: new Date(),
      status: 'pending',
    };
    dispatch({ type: 'ADD_SYSTEM_MESSAGE', message: systemMessage });

    // Add pending assistant message for agent response
    const assistantMessageId = generateId();
    addPendingAssistantMessage(assistantMessageId);

    dispatch({ type: 'SET_AGENT_STATUS', status: 'starting' });

    try {
      const { sessionId } = await chatService.startSession('start');
      setSessionId(sessionId);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to initialize session';
      dispatch({ type: 'SET_ERROR', error: errorMessage });
      completeAssistantMessage();
    }
  }, [addPendingAssistantMessage, setSessionId, completeAssistantMessage]);

  // Handle SSE messages
  const handleSSEMessage = useCallback((message: StreamMessage) => {
    // Check if message belongs to our session (uses session_id only per ADR-010)
    const isOurSession = (msg: StreamMessage): boolean => {
      if (!sessionIdRef.current) return false;
      if ('session' in msg && msg.session) {
        return msg.session.session_id === sessionIdRef.current;
      }
      if ('data' in msg && msg.data) {
        return msg.data.session_id === sessionIdRef.current;
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
        case 'run_start':
          dispatch({ type: 'SET_AGENT_STATUS', status: 'running' });
          break;

        case 'run_completed':
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
              // Remove "Session initializing..." system message when agent responds
              dispatch({ type: 'REMOVE_SYSTEM_MESSAGES' });

              if (pendingMessageIdRef.current) {
                // Update existing pending message
                dispatch({ type: 'UPDATE_ASSISTANT_MESSAGE', content: textContent });
              } else {
                // No pending message - agent sent additional response after run_completed
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

  // Subscribe to SSE - use ref pattern to avoid re-subscription
  const handlerRef = useRef(handleSSEMessage);
  handlerRef.current = handleSSEMessage;

  useEffect(() => {
    const stableHandler = (msg: StreamMessage) => handlerRef.current(msg);
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
      if (!state.sessionId) {
        // First message: start new session
        const { sessionId } = await chatService.startSession(prompt);
        setSessionId(sessionId);
      } else {
        // Session exists (status=finished means idle, ready to resume)
        await chatService.resumeSession(state.sessionId, prompt);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      dispatch({ type: 'SET_ERROR', error: errorMessage });
      completeAssistantMessage();
    }
  }, [state.sessionId, addPendingAssistantMessage, setSessionId, completeAssistantMessage]);

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

  // Reset chat and auto-initialize (for header "New Chat" button)
  const resetChat = useCallback(async () => {
    resetChatState();
    await initializeChat();
  }, [resetChatState, initializeChat]);

  return (
    <ChatContext.Provider value={{ state, sendMessage, stopAgent, resetChat, initializeChat }}>
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
