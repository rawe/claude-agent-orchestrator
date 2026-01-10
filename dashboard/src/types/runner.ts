export type RunnerStatus = 'online' | 'stale' | 'offline';

// Details about the executor binary
export interface ExecutorDetails {
  type: string;
  command: string;
  args?: string[];
  working_dir?: string;
  config?: Record<string, unknown>;  // Arbitrary executor-specific configuration
  agents_dir?: string | null;        // Path to agents directory (for procedural executors)
}

export interface Runner {
  runner_id: string;
  registered_at: string;
  last_heartbeat: string;
  hostname: string | null;
  project_dir: string | null;
  executor_profile: string | null;  // Was executor_type
  executor?: ExecutorDetails;        // Executor details from runner
  tags: string[];  // Capability tags (ADR-011)
  require_matching_tags?: boolean;   // If true, run must have at least one matching tag
  status: RunnerStatus;
  seconds_since_heartbeat: number;
}
