/**
 * Unified View Service
 *
 * Provides a unified data layer for the Session-Run views.
 * Fetches real data from the backend and transforms it into
 * enriched types suitable for all visualization approaches.
 *
 * Design principles:
 * - No magic strings (use enums/constants from types)
 * - Clean separation between backend types and view types
 * - Computed fields derived from combining sessions + runs
 * - Zero backend changes required
 */

import { sessionService, runService } from '@/services';
import type { Session, Run, SessionEvent } from '@/types';
import {
  UnifiedSession,
  UnifiedRun,
  UnifiedEvent,
  RunStatusValues,
  EventTypeValues,
} from './unifiedViewTypes';

// ============================================================================
// ADAPTERS: Transform backend types to unified view types
// ============================================================================

/**
 * Adapter to transform backend Session + associated Runs into UnifiedSession
 */
function adaptSession(
  session: Session,
  sessionRuns: Run[]
): UnifiedSession {
  // Sort runs by created_at to determine run numbers
  const sortedRuns = [...sessionRuns].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  // Compute latest run status
  const latestRun = sortedRuns[sortedRuns.length - 1];
  const latestRunStatus = latestRun?.status ?? RunStatusValues.PENDING;

  // Derive display name from session_id (strip prefix for cleaner display)
  // Format: ses_abc123def456 -> abc123def456
  const displayName = session.session_id.startsWith('ses_')
    ? session.session_id.slice(4)
    : session.session_id;

  return {
    sessionId: session.session_id,
    displayName,
    agentName: session.agent_name ?? null,
    status: session.status as UnifiedSession['status'],
    createdAt: session.created_at,
    modifiedAt: session.modified_at ?? null,
    projectDir: session.project_dir ?? null,
    parentSessionId: session.parent_session_id ?? null,
    executorSessionId: session.executor_session_id ?? null,
    executorType: session.executor_type ?? null,
    hostname: session.hostname ?? null,
    // Computed fields
    runCount: sortedRuns.length,
    latestRunStatus,
  };
}

/**
 * Adapter to transform backend Run into UnifiedRun
 */
function adaptRun(
  run: Run,
  runNumber: number,
  events: UnifiedEvent[] = []
): UnifiedRun {
  return {
    runId: run.run_id,
    sessionId: run.session_id,
    type: run.type as UnifiedRun['type'],
    status: run.status as UnifiedRun['status'],
    prompt: run.prompt,
    agentName: run.agent_name ?? null,
    projectDir: run.project_dir ?? null,
    parentSessionId: run.parent_session_id ?? null,
    executionMode: run.execution_mode,
    runnerId: run.runner_id ?? null,
    error: run.error ?? null,
    createdAt: run.created_at,
    claimedAt: run.claimed_at ?? null,
    startedAt: run.started_at ?? null,
    completedAt: run.completed_at ?? null,
    // Computed field
    runNumber,
    // Events (populated separately if needed)
    events,
  };
}

/**
 * Adapter to transform backend SessionEvent into UnifiedEvent
 */
function adaptEvent(event: SessionEvent): UnifiedEvent {
  // Extract summary based on event type
  let summary = '';

  switch (event.event_type) {
    case EventTypeValues.SESSION_START:
      summary = 'Session started';
      break;
    case EventTypeValues.SESSION_STOP:
      summary = event.reason ?? `Session stopped (exit code: ${event.exit_code ?? 'unknown'})`;
      break;
    case EventTypeValues.PRE_TOOL:
      summary = `Calling: ${event.tool_name ?? 'unknown tool'}`;
      break;
    case EventTypeValues.POST_TOOL:
      if (event.error) {
        summary = `${event.tool_name ?? 'Tool'} failed: ${event.error}`;
      } else {
        summary = `${event.tool_name ?? 'Tool'} completed`;
      }
      break;
    case EventTypeValues.MESSAGE:
      if (event.role === 'assistant' && event.content?.[0]) {
        const text = event.content[0].text ?? '';
        summary = text.length > 100 ? text.slice(0, 100) + '...' : text;
      } else if (event.role === 'user') {
        summary = 'User message';
      } else {
        summary = 'Message';
      }
      break;
    default:
      summary = event.event_type;
  }

  return {
    id: event.id ?? 0,
    sessionId: event.session_id,
    eventType: event.event_type as UnifiedEvent['eventType'],
    timestamp: event.timestamp,
    toolName: event.tool_name ?? null,
    toolInput: event.tool_input ?? null,
    toolOutput: event.tool_output ?? null,
    error: event.error ?? null,
    exitCode: event.exit_code ?? null,
    reason: event.reason ?? null,
    role: event.role as UnifiedEvent['role'] ?? null,
    content: event.content ?? null,
    // Computed field
    summary,
  };
}

// ============================================================================
// SERVICE: Unified data fetching and transformation
// ============================================================================

export interface UnifiedViewData {
  sessions: UnifiedSession[];
  runs: UnifiedRun[];
  /** Map of sessionId -> UnifiedRun[] for quick lookup */
  runsBySession: Map<string, UnifiedRun[]>;
  /** Map of sessionId -> UnifiedSession for quick lookup */
  sessionsById: Map<string, UnifiedSession>;
}

export const unifiedViewService = {
  /**
   * Fetch all sessions and runs, returning unified/enriched data
   */
  async getUnifiedData(): Promise<UnifiedViewData> {
    // Fetch sessions and runs in parallel
    const [rawSessions, rawRuns] = await Promise.all([
      sessionService.getSessions(),
      runService.getRuns(),
    ]);

    // Group runs by session_id
    const runsBySessionId = new Map<string, Run[]>();
    for (const run of rawRuns) {
      const existing = runsBySessionId.get(run.session_id) ?? [];
      existing.push(run);
      runsBySessionId.set(run.session_id, existing);
    }

    // Transform sessions with their runs
    const sessions: UnifiedSession[] = rawSessions.map((session) => {
      const sessionRuns = runsBySessionId.get(session.session_id) ?? [];
      return adaptSession(session, sessionRuns);
    });

    // Transform runs with computed run numbers
    const runs: UnifiedRun[] = [];
    const runsBySession = new Map<string, UnifiedRun[]>();

    for (const session of rawSessions) {
      const sessionRuns = runsBySessionId.get(session.session_id) ?? [];
      // Sort by created_at to assign run numbers
      const sortedRuns = [...sessionRuns].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );

      const unifiedRuns: UnifiedRun[] = sortedRuns.map((run, index) =>
        adaptRun(run, index + 1)
      );

      runs.push(...unifiedRuns);
      runsBySession.set(session.session_id, unifiedRuns);
    }

    // Build session lookup map
    const sessionsById = new Map<string, UnifiedSession>();
    for (const session of sessions) {
      sessionsById.set(session.sessionId, session);
    }

    return {
      sessions,
      runs,
      runsBySession,
      sessionsById,
    };
  },

  /**
   * Fetch events for a specific session
   */
  async getSessionEvents(sessionId: string): Promise<UnifiedEvent[]> {
    const rawEvents = await sessionService.getSessionEvents(sessionId);
    return rawEvents.map(adaptEvent);
  },

  /**
   * Fetch a single run with its events
   */
  async getRunWithEvents(
    runId: string,
    sessionId: string,
    runNumber: number
  ): Promise<UnifiedRun | null> {
    try {
      const [rawRun, rawEvents] = await Promise.all([
        runService.getRun(runId),
        sessionService.getSessionEvents(sessionId),
      ]);

      // Filter events that occurred during this run's time window
      const runEvents = filterEventsForRun(rawEvents, rawRun);
      const unifiedEvents = runEvents.map(adaptEvent);

      return adaptRun(rawRun, runNumber, unifiedEvents);
    } catch {
      return null;
    }
  },

  /**
   * Get child sessions for a parent session
   */
  getChildSessions(
    allSessions: UnifiedSession[],
    parentSessionId: string
  ): UnifiedSession[] {
    return allSessions.filter((s) => s.parentSessionId === parentSessionId);
  },

  /**
   * Get root sessions (no parent)
   */
  getRootSessions(allSessions: UnifiedSession[]): UnifiedSession[] {
    return allSessions.filter((s) => s.parentSessionId === null);
  },

  /**
   * Build a hierarchical tree of sessions
   */
  buildSessionTree(
    sessions: UnifiedSession[],
    runsBySession: Map<string, UnifiedRun[]>
  ): SessionTreeNode[] {
    const rootSessions = this.getRootSessions(sessions);

    const buildNode = (session: UnifiedSession): SessionTreeNode => {
      const sessionRuns = runsBySession.get(session.sessionId) ?? [];
      const childSessions = this.getChildSessions(sessions, session.sessionId);

      return {
        session,
        runs: sessionRuns,
        children: childSessions.map(buildNode),
      };
    };

    return rootSessions.map(buildNode);
  },
};

/**
 * Filter events that occurred during a run's execution window
 */
function filterEventsForRun(events: SessionEvent[], run: Run): SessionEvent[] {
  const runStart = run.started_at ? new Date(run.started_at).getTime() : null;
  const runEnd = run.completed_at ? new Date(run.completed_at).getTime() : null;

  if (!runStart) {
    // Run hasn't started, no events yet
    return [];
  }

  return events.filter((event) => {
    const eventTime = new Date(event.timestamp).getTime();

    // Event must be after run start
    if (eventTime < runStart) {
      return false;
    }

    // If run completed, event must be before completion
    if (runEnd && eventTime > runEnd) {
      return false;
    }

    return true;
  });
}

// ============================================================================
// TREE TYPES
// ============================================================================

export interface SessionTreeNode {
  session: UnifiedSession;
  runs: UnifiedRun[];
  children: SessionTreeNode[];
}
