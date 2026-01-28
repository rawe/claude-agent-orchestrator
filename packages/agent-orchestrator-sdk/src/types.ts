/**
 * Coordinator Client Types
 *
 * MVP SDK for programmatic interaction with the Agent Coordinator.
 */

/**
 * Configuration for initializing the CoordinatorClient.
 */
export interface CoordinatorClientConfig {
  /** Base URL of the Agent Coordinator API (e.g., "http://localhost:8765") */
  baseUrl: string;

  /** Optional function to get auth token. Called before each request. */
  getToken?: () => Promise<string | null>;
}

/**
 * Options for starting a new run.
 */
export interface StartRunOptions {
  /** Agent name. If omitted, uses generic agent. */
  agentName?: string;

  /** Input parameters (e.g., { prompt: "..." } for generic agent) */
  parameters: Record<string, unknown>;

  /** Optional project directory context */
  projectDir?: string;
}

/**
 * Response from starting a run.
 */
export interface StartRunResponse {
  runId: string;
  sessionId: string;
  status: string;
}

/**
 * Session status values.
 */
export type SessionStatus = 'pending' | 'running' | 'stopping' | 'finished' | 'stopped' | 'not_existent';

/**
 * Final result from a completed run.
 */
export interface RunResult {
  status: 'completed' | 'failed' | 'stopped';
  resultText?: string;
  resultData?: Record<string, unknown>;
  error?: string;
}

/**
 * API response for session status check.
 */
export interface SessionStatusResponse {
  status: SessionStatus;
}

/**
 * API response for session result.
 */
export interface SessionResultResponse {
  result_text: string | null;
  result_data: Record<string, unknown> | null;
}
