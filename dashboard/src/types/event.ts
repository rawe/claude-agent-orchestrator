export type EventType = 'session_start' | 'session_stop' | 'pre_tool' | 'post_tool' | 'message';

export type MessageRole = 'user' | 'assistant';

export interface MessageContent {
  type: 'text' | 'tool_use' | 'tool_result';
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
  content?: unknown;
}

export interface SessionEvent {
  id?: number;
  session_id: string;
  event_type: EventType;
  timestamp: string;
  // Tool events
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: unknown;
  error?: string;
  // Session stop events
  exit_code?: number;
  reason?: string;
  // Message events
  role?: MessageRole;
  content?: MessageContent[];
}

export interface StreamMessage {
  type: 'init' | 'event' | 'session_created' | 'session_updated' | 'session_deleted';
  sessions?: import('./session').Session[];
  data?: SessionEvent;
  session?: import('./session').Session;
  session_id?: string;
}
