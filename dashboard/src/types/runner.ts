export type RunnerStatus = 'online' | 'stale' | 'offline';

export interface Runner {
  runner_id: string;
  registered_at: string;
  last_heartbeat: string;
  hostname: string | null;
  project_dir: string | null;
  executor_type: string | null;
  status: RunnerStatus;
  seconds_since_heartbeat: number;
}
