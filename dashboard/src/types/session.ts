/**
 * Session types for Agent Orchestrator Dashboard
 *
 * Note: Uses session_id (coordinator-generated) per ADR-010.
 */

export type SessionStatus = 'pending' | 'running' | 'stopping' | 'finished' | 'stopped';

export interface Session {
  session_id: string;
  status: SessionStatus;
  created_at: string;
  modified_at?: string;
  project_dir?: string;
  agent_name?: string;
  parent_session_id?: string;
  // Executor affinity data (ADR-010)
  executor_session_id?: string;
  executor_type?: string;
  hostname?: string;
}

export interface SessionMetadataUpdate {
  project_dir?: string;
  agent_name?: string;
}
