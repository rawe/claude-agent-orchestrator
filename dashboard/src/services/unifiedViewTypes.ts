/**
 * Unified View Types
 *
 * Type definitions for the unified session-run views.
 * These are "enriched" types that include computed fields
 * derived from combining backend data.
 *
 * Design principles:
 * - No magic strings - use exported constants for all string literals
 * - camelCase property names (TypeScript convention)
 * - Nullable fields explicitly marked
 * - Computed fields documented
 */

// ============================================================================
// STATUS & TYPE CONSTANTS (No Magic Strings)
// ============================================================================

/**
 * Session status values - matches backend SessionStatus
 */
export const SessionStatusValues = {
  PENDING: 'pending',
  RUNNING: 'running',
  STOPPING: 'stopping',
  FINISHED: 'finished',
  STOPPED: 'stopped',
} as const;

export type SessionStatus = (typeof SessionStatusValues)[keyof typeof SessionStatusValues];

/**
 * Run status values - matches backend RunStatus
 */
export const RunStatusValues = {
  PENDING: 'pending',
  CLAIMED: 'claimed',
  RUNNING: 'running',
  STOPPING: 'stopping',
  COMPLETED: 'completed',
  FAILED: 'failed',
  STOPPED: 'stopped',
} as const;

export type RunStatus = (typeof RunStatusValues)[keyof typeof RunStatusValues];

/**
 * Run type values - matches backend RunType
 */
export const RunTypeValues = {
  START_SESSION: 'start_session',
  RESUME_SESSION: 'resume_session',
} as const;

export type RunType = (typeof RunTypeValues)[keyof typeof RunTypeValues];

/**
 * Execution mode values - matches backend ExecutionMode
 */
export const ExecutionModeValues = {
  SYNC: 'sync',
  ASYNC_POLL: 'async_poll',
  ASYNC_CALLBACK: 'async_callback',
} as const;

export type ExecutionMode = (typeof ExecutionModeValues)[keyof typeof ExecutionModeValues];

/**
 * Event type values - matches backend SessionEventType
 */
export const EventTypeValues = {
  SESSION_START: 'session_start',
  SESSION_STOP: 'session_stop',
  PRE_TOOL: 'pre_tool',
  POST_TOOL: 'post_tool',
  MESSAGE: 'message',
} as const;

export type EventType = (typeof EventTypeValues)[keyof typeof EventTypeValues];

/**
 * Message role values
 */
export const MessageRoleValues = {
  USER: 'user',
  ASSISTANT: 'assistant',
} as const;

export type MessageRole = (typeof MessageRoleValues)[keyof typeof MessageRoleValues];

// ============================================================================
// HELPER FUNCTIONS FOR STATUS CHECKS
// ============================================================================

/**
 * Check if a session is currently active (running or stopping)
 */
export function isSessionActive(status: SessionStatus): boolean {
  return status === SessionStatusValues.RUNNING || status === SessionStatusValues.STOPPING;
}

/**
 * Check if a run is currently active (not terminal state)
 */
export function isRunActive(status: RunStatus): boolean {
  return (
    status === RunStatusValues.PENDING ||
    status === RunStatusValues.CLAIMED ||
    status === RunStatusValues.RUNNING ||
    status === RunStatusValues.STOPPING
  );
}

/**
 * Check if a run is in a terminal state
 */
export function isRunTerminal(status: RunStatus): boolean {
  return (
    status === RunStatusValues.COMPLETED ||
    status === RunStatusValues.FAILED ||
    status === RunStatusValues.STOPPED
  );
}

/**
 * Check if a run type is start (vs resume)
 */
export function isStartRun(type: RunType): boolean {
  return type === RunTypeValues.START_SESSION;
}

// ============================================================================
// UNIFIED TYPES (Enriched with computed fields)
// ============================================================================

/**
 * Unified Session - enriched session with computed fields
 *
 * Combines backend Session with run statistics
 */
export interface UnifiedSession {
  // Core identity
  sessionId: string;
  /** Display-friendly name derived from sessionId */
  displayName: string;

  // Metadata
  agentName: string | null;
  status: SessionStatus;
  createdAt: string;
  modifiedAt: string | null;
  projectDir: string | null;

  // Hierarchy
  parentSessionId: string | null;

  // Executor info (populated after bind)
  executorSessionId: string | null;
  executorProfile: string | null;  // Was executorType
  hostname: string | null;

  // ---- COMPUTED FIELDS ----
  /** Number of runs for this session */
  runCount: number;
  /** Status of the most recent run */
  latestRunStatus: RunStatus;
}

/**
 * Unified Run - enriched run with computed fields
 */
export interface UnifiedRun {
  // Core identity
  runId: string;
  sessionId: string;

  // Run info
  type: RunType;
  status: RunStatus;
  prompt: string;
  agentName: string | null;
  projectDir: string | null;
  parentSessionId: string | null;
  executionMode: ExecutionMode;

  // Execution info
  runnerId: string | null;
  error: string | null;

  // Timestamps
  createdAt: string;
  claimedAt: string | null;
  startedAt: string | null;
  completedAt: string | null;

  // ---- COMPUTED FIELDS ----
  /** 1-based run number within the session */
  runNumber: number;
  /** Events that occurred during this run (populated on demand) */
  events: UnifiedEvent[];
}

/**
 * Unified Event - enriched event with computed fields
 */
export interface UnifiedEvent {
  // Core identity
  id: number;
  sessionId: string;

  // Event info
  eventType: EventType;
  timestamp: string;

  // Tool event fields
  toolName: string | null;
  toolInput: Record<string, unknown> | null;
  toolOutput: unknown | null;
  error: string | null;

  // Session stop fields
  exitCode: number | null;
  reason: string | null;

  // Message fields
  role: MessageRole | null;
  content: MessageContent[] | null;

  // ---- COMPUTED FIELDS ----
  /** Human-readable summary of the event */
  summary: string;
}

/**
 * Message content block
 */
export interface MessageContent {
  type: 'text' | 'tool_use' | 'tool_result';
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
  content?: unknown;
}

// ============================================================================
// ACTIVITY FEED TYPES
// ============================================================================

/**
 * Activity type values for the activity feed
 */
export const ActivityTypeValues = {
  RUN_STARTED: 'run_started',
  RUN_COMPLETED: 'run_completed',
  RUN_FAILED: 'run_failed',
  RUN_STOPPED: 'run_stopped',
  SESSION_EVENT: 'session_event',
} as const;

export type ActivityType = (typeof ActivityTypeValues)[keyof typeof ActivityTypeValues];

/**
 * Base activity item
 */
export interface BaseActivityItem {
  id: string;
  timestamp: string;
  type: ActivityType;
  sessionId: string;
  sessionDisplayName: string;
  agentName: string | null;
}

/**
 * Run activity item (started, completed, failed, stopped)
 */
export interface RunActivityItem extends BaseActivityItem {
  type: 'run_started' | 'run_completed' | 'run_failed' | 'run_stopped';
  run: UnifiedRun;
}

/**
 * Event activity item (session events)
 */
export interface EventActivityItem extends BaseActivityItem {
  type: 'session_event';
  event: UnifiedEvent;
  runId?: string;
}

export type ActivityItem = RunActivityItem | EventActivityItem;

// ============================================================================
// VIEW TAB TYPES
// ============================================================================

/**
 * Tab identifiers for the unified view
 */
export const TabIdValues = {
  SESSION_TIMELINE: 'session-timeline',
  RUN_CENTRIC: 'run-centric',
  TREE_VIEW: 'tree-view',
  SWIMLANE: 'swimlane',
  ACTIVITY_FEED: 'activity-feed',
  DASHBOARD_CARDS: 'dashboard-cards',
} as const;

export type TabId = (typeof TabIdValues)[keyof typeof TabIdValues];

/**
 * Tab configuration
 */
export interface TabConfig {
  id: TabId;
  label: string;
  description: string;
}

/**
 * All available tabs
 */
export const UNIFIED_VIEW_TABS: TabConfig[] = [
  {
    id: TabIdValues.SESSION_TIMELINE,
    label: 'Session Timeline',
    description: 'Session-centric view with run blocks',
  },
  {
    id: TabIdValues.RUN_CENTRIC,
    label: 'Run Centric',
    description: 'Run list with session context panel',
  },
  {
    id: TabIdValues.TREE_VIEW,
    label: 'Tree View',
    description: 'Hierarchical session/run tree',
  },
  {
    id: TabIdValues.SWIMLANE,
    label: 'Swimlane',
    description: 'Timeline swimlanes by session',
  },
  {
    id: TabIdValues.ACTIVITY_FEED,
    label: 'Activity Feed',
    description: 'Chronological activity stream',
  },
  {
    id: TabIdValues.DASHBOARD_CARDS,
    label: 'Dashboard',
    description: 'Overview cards with drill-down',
  },
];
