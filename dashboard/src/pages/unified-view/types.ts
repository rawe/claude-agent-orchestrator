// Types for the Unified View

export interface MockSession {
  session_id: string;
  name: string;
  agent_name: string;
  status: 'running' | 'finished' | 'stopped';
  created_at: string;
  project_dir?: string;
  parent_session_id: string | null;
  runCount: number;
  latestRunStatus: 'pending' | 'claimed' | 'running' | 'stopping' | 'completed' | 'failed' | 'stopped';
}

export interface MockRun {
  run_id: string;
  session_id: string;
  type: 'start_session' | 'resume_session';
  status: 'pending' | 'claimed' | 'running' | 'stopping' | 'completed' | 'failed' | 'stopped';
  prompt: string;
  created_at: string;
  started_at?: string;
  completed_at?: string | null;
  runner_id?: string;
  agent_name: string;
  runNumber: number;
  events: { type: string; timestamp: string; summary: string }[];
  error?: string;
}

// Activity Feed types
export type ActivityType = 'run_started' | 'run_completed' | 'run_failed' | 'run_stopped' | 'session_event';

export interface BaseActivityItem {
  id: string;
  timestamp: string;
  type: ActivityType;
  sessionId: string;
  sessionName: string;
  agentName: string;
}

export interface RunActivityItem extends BaseActivityItem {
  type: 'run_started' | 'run_completed' | 'run_failed' | 'run_stopped';
  run: MockRun;
  runNumber: number;
}

export interface EventActivityItem extends BaseActivityItem {
  type: 'session_event';
  eventType: string;
  summary: string;
  runId?: string;
}

export type ActivityItem = RunActivityItem | EventActivityItem;

export type TabId = 'session-timeline' | 'run-centric' | 'tree-view' | 'swimlane' | 'activity-feed' | 'dashboard-cards';
