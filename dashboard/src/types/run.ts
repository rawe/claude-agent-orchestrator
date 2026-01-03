export type RunType = 'start_session' | 'resume_session';

export type RunStatus = 'pending' | 'claimed' | 'running' | 'stopping' | 'completed' | 'failed' | 'stopped';

export type ExecutionMode = 'sync' | 'async_poll' | 'async_callback';

export interface RunDemands {
  hostname?: string | null;
  project_dir?: string | null;
  executor_profile?: string | null;  // Was executor_type
  tags?: string[];
}

export interface Run {
  run_id: string;
  type: RunType;
  session_id: string;
  agent_name: string | null;
  prompt: string;
  project_dir: string | null;
  parent_session_id: string | null;
  execution_mode: ExecutionMode;
  demands: RunDemands | null;
  status: RunStatus;
  runner_id: string | null;
  error: string | null;
  created_at: string;
  claimed_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  timeout_at: string | null;
}

export interface StopRunResponse {
  ok: boolean;
  run_id: string;
  session_id: string;
  status: string;
  message?: string;
}
