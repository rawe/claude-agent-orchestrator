/**
 * Types matching Agent Coordinator API models
 * See: docs/components/agent-coordinator/DATA_MODELS.md
 */

// Message content block
export interface ContentBlock {
  type: 'text';
  text?: string;
}

// Event from SSE stream
export interface SessionEvent {
  event_type: 'run_start' | 'run_completed' | 'pre_tool' | 'post_tool' | 'message' | 'result';
  session_id: string;
  timestamp: string;

  // Tool events
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: unknown;
  error?: string;

  // Run completion events
  exit_code?: number;
  reason?: string;

  // Message events
  role?: 'user' | 'assistant';
  content?: ContentBlock[];

  // Result events (for event_type='result')
  result_text?: string;
  result_data?: Record<string, unknown>;
}

// Session object
export interface Session {
  session_id: string;
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
  parent_session_id?: string;
}

// Stream message types
export type StreamMessage =
  | { type: 'init'; sessions: Session[] }
  | { type: 'session_created'; session: Session }
  | { type: 'session_updated'; session: Session }
  | { type: 'session_deleted'; session_id: string }
  | { type: 'event'; data: SessionEvent };

// Run request (POST /runs)
export interface RunRequest {
  type: 'start_session' | 'resume_session';
  session_id?: string;  // Required for resume_session
  parameters: Record<string, unknown>;  // Unified input - e.g., {"prompt": "..."} for AI agents
  agent_name?: string;
  project_dir?: string;
  parent_session_id?: string;
}

// Run response
export interface RunResponse {
  run_id: string;
  session_id: string;
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

// Parameter Validation Error Types (Phase 3: Schema Discovery & Validation)
export interface ValidationError {
  path: string;          // JSON path to the invalid field (e.g., "$.prompt")
  message: string;       // Human-readable error message
  schema_path: string;   // Path in schema where constraint is defined
}

export interface ParameterValidationErrorResponse {
  error: 'parameter_validation_failed';
  message: string;
  agent_name: string;
  validation_errors: ValidationError[];
  parameters_schema: Record<string, unknown>;
}

export function isParameterValidationError(
  error: unknown
): error is ParameterValidationErrorResponse {
  return (
    typeof error === 'object' &&
    error !== null &&
    'error' in error &&
    (error as Record<string, unknown>).error === 'parameter_validation_failed'
  );
}
