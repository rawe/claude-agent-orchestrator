export interface Launcher {
  launcher_id: string;
  registered_at: string;
  last_heartbeat: string;
  hostname: string | null;
  project_dir: string | null;
  is_alive: boolean;
}
