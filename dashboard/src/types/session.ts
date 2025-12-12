export type SessionStatus = 'running' | 'stopping' | 'finished' | 'stopped';

export interface Session {
  session_id: string;
  session_name?: string;
  status: SessionStatus;
  created_at: string;
  modified_at?: string;
  project_dir?: string;
  agent_name?: string;
  parent_session_name?: string;
}

export interface SessionMetadataUpdate {
  session_name?: string;
  project_dir?: string;
  agent_name?: string;
}
