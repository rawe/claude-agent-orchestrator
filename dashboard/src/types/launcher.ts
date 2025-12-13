export type LauncherStatus = 'online' | 'stale' | 'offline';

export interface Launcher {
  launcher_id: string;
  registered_at: string;
  last_heartbeat: string;
  hostname: string | null;
  project_dir: string | null;
  executor_type: string | null;
  status: LauncherStatus;
  seconds_since_heartbeat: number;
}
