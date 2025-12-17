/**
 * Types matching Agent Coordinator API models
 * See: docs/agent-coordinator/DATA_MODELS.md
 */

// Message content block
export interface ContentBlock {
  type: 'text';
  text?: string;
}

// Event from WebSocket
export interface SessionEvent {
  event_type: 'session_start' | 'session_stop' | 'pre_tool' | 'post_tool' | 'message';
  session_id: string;
  session_name?: string;
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
  role?: 'user' | 'assistant';
  content?: ContentBlock[];
}

// Session object
export interface Session {
  session_id: string;
  session_name: string;
  /**
   * Session status:
   * - 'running': Agent is actively processing
   * - 'finished': Agent is idle, ready for new input (can be resumed)
   */
  status: 'running' | 'finished';
  created_at?: string;
  project_dir?: string;
  agent_name?: string;
  last_resumed_at?: string;
  parent_session_name?: string;
}

// WebSocket message types
export type WebSocketMessage =
  | { type: 'init'; sessions: Session[] }
  | { type: 'session_created'; session: Session }
  | { type: 'session_updated'; session: Session }
  | { type: 'session_deleted'; session_id: string }
  | { type: 'event'; data: SessionEvent };

// Job request (POST /jobs)
export interface JobRequest {
  type: 'start_session' | 'resume_session';
  session_name: string;
  prompt: string;
  agent_name?: string;
  project_dir?: string;
  parent_session_name?: string;
}

// Job response
export interface JobResponse {
  job_id: string;
  status: string;
}

// Tool call tracking (UI only)
export interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'error';
  timestamp: Date;
  input?: Record<string, unknown>;
  output?: unknown;
  error?: string;
}

// Chat message for display (UI only)
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status: 'pending' | 'complete' | 'error';
  toolCalls?: ToolCall[];
}

// Agent status (UI only)
export type AgentStatus = 'idle' | 'starting' | 'running' | 'stopping' | 'finished' | 'error';
