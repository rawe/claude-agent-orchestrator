export type RunnerStatus = 'online' | 'stale' | 'offline';

export interface Runner {
  runner_id: string;
  registered_at: string;
  last_heartbeat: string;
  hostname: string | null;
  project_dir: string | null;
  executor_type: string | null;
  tags: string[];  // Capability tags (ADR-011)
  status: RunnerStatus;
  seconds_since_heartbeat: number;
}
