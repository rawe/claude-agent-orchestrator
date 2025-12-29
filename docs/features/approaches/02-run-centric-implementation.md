# Approach 2: Run-Centric View with Session Context Panel

## Status

**Implementation Guide** - Ready for Development

## Overview

This approach presents **runs as the primary entity** with a two-panel layout. The left panel shows a scrollable run list, while the right panel provides session context for the selected run and a filtered events stream.

## Architecture Overview

```
┌────────────────────────────────┬──────────────────────────────────────┐
│                                │  SESSION CONTEXT PANEL               │
│      RUN LIST                  │  - Session metadata                  │
│      (Primary)                 │  - Run history for session           │
│                                │  - Child sessions                    │
│  ┌──────────────────────────┐  ├──────────────────────────────────────┤
│  │ Run abc123               │  │                                      │
│  │ Session: orchestrator    │  │  EVENTS STREAM                       │
│  │ Status: running          │  │  (filtered by run time window)       │
│  └──────────────────────────┘  │                                      │
│                                │  - session_start                     │
│  ┌──────────────────────────┐  │  - tool_call                         │
│  │ Run def456               │  │  - message                           │
│  │ Session: child-1         │  │  - session_stop                      │
│  │ Status: completed        │  │                                      │
│  └──────────────────────────┘  │                                      │
│                                │                                      │
└────────────────────────────────┴──────────────────────────────────────┘
```

## Component Diagram

```
UnifiedViewPage
  │
  ├── TabNavigation (shared across all 6 approaches)
  │     ├── Tab: "Session Timeline"   (Approach 1)
  │     ├── Tab: "Run Centric"        (Approach 2) <-- THIS ONE
  │     ├── Tab: "Tree View"          (Approach 3)
  │     ├── Tab: "Swimlane"           (Approach 4)
  │     ├── Tab: "Activity Feed"      (Approach 5)
  │     └── Tab: "Dashboard Cards"    (Approach 6)
  │
  └── RunCentricTab
        │
        ├── RunListPanel (left)
        │     ├── RunFilterBar
        │     └── RunListItem (repeated)
        │           ├── RunStatusBadge (existing)
        │           └── SessionBadge (new)
        │
        └── ContextPanel (right)
              ├── SessionContextHeader
              │     ├── SessionMetadata
              │     ├── RunHistoryCompact
              │     └── ChildSessionsList
              │
              └── RunEventsStream
                    └── EventTimeline (adapted from existing)
```

## Shared Infrastructure Components

These components are designed to be shared across all 6 tab approaches.

### 1. Combined Session+Run Data Hook

```typescript
// File: /dashboard/src/hooks/useSessionsWithRuns.ts

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSessions } from '@/contexts';
import { runService } from '@/services';
import type { Session, Run } from '@/types';

export interface SessionWithRuns extends Session {
  runs: Run[];
  childSessions?: SessionWithRuns[];
}

export interface RunWithSession extends Run {
  session: Session | null;
}

interface UseSessionsWithRunsOptions {
  autoRefreshInterval?: number;
  includeChildren?: boolean;
}

interface UseSessionsWithRunsReturn {
  sessions: SessionWithRuns[];
  runs: RunWithSession[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  getRunsForSession: (sessionId: string) => Run[];
  getSessionForRun: (runId: string) => Session | null;
}

export function useSessionsWithRuns(
  options: UseSessionsWithRunsOptions = {}
): UseSessionsWithRunsReturn {
  const { autoRefreshInterval = 5000, includeChildren = true } = options;

  const { sessions: baseSessions, loading: sessionsLoading } = useSessions();
  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await runService.getRuns();
      setRuns(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runs');
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (autoRefreshInterval <= 0) return;
    const interval = setInterval(fetchRuns, autoRefreshInterval);
    return () => clearInterval(interval);
  }, [autoRefreshInterval, fetchRuns]);

  // Build session ID to runs lookup
  const sessionRunsMap = useMemo(() => {
    const map = new Map<string, Run[]>();
    runs.forEach(run => {
      const existing = map.get(run.session_id) || [];
      existing.push(run);
      map.set(run.session_id, existing);
    });
    map.forEach((runList) => {
      runList.sort((a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
    });
    return map;
  }, [runs]);

  // Build run ID to session lookup
  const runSessionMap = useMemo(() => {
    const map = new Map<string, Session>();
    baseSessions.forEach(session => {
      const sessionRuns = sessionRunsMap.get(session.session_id) || [];
      sessionRuns.forEach(run => {
        map.set(run.run_id, session);
      });
    });
    return map;
  }, [baseSessions, sessionRunsMap]);

  // Enrich sessions with runs
  const sessionsWithRuns = useMemo((): SessionWithRuns[] => {
    return baseSessions.map(session => ({
      ...session,
      runs: sessionRunsMap.get(session.session_id) || [],
      childSessions: includeChildren
        ? baseSessions
            .filter(s => s.parent_session_id === session.session_id)
            .map(child => ({
              ...child,
              runs: sessionRunsMap.get(child.session_id) || [],
            }))
        : undefined,
    }));
  }, [baseSessions, sessionRunsMap, includeChildren]);

  // Enrich runs with session
  const runsWithSession = useMemo((): RunWithSession[] => {
    return runs.map(run => ({
      ...run,
      session: runSessionMap.get(run.run_id) || null,
    }));
  }, [runs, runSessionMap]);

  return {
    sessions: sessionsWithRuns,
    runs: runsWithSession,
    loading: sessionsLoading || runsLoading,
    error,
    refresh: fetchRuns,
    getRunsForSession: (sessionId: string) => sessionRunsMap.get(sessionId) || [],
    getSessionForRun: (runId: string) => runSessionMap.get(runId) || null,
  };
}
```

### 2. Run Time Window Filter Utility

```typescript
// File: /dashboard/src/utils/runTimeFilter.ts

import type { Run, SessionEvent } from '@/types';

export interface TimeWindow {
  start: Date | null;
  end: Date | null;
}

export function getRunTimeWindow(run: Run): TimeWindow {
  return {
    start: run.started_at ? new Date(run.started_at) : null,
    end: run.completed_at ? new Date(run.completed_at) : null,
  };
}

export function isEventInTimeWindow(
  event: SessionEvent,
  window: TimeWindow
): boolean {
  if (!window.start) return false;

  const eventTime = new Date(event.timestamp);
  const afterStart = eventTime >= window.start;
  const beforeEnd = window.end === null || eventTime <= window.end;

  return afterStart && beforeEnd;
}

export function filterEventsByRun(
  events: SessionEvent[],
  run: Run
): SessionEvent[] {
  const window = getRunTimeWindow(run);
  return events.filter(event => isEventInTimeWindow(event, window));
}

export function formatRunTimeRange(run: Run): string {
  if (!run.started_at) return 'Not started';

  const start = new Date(run.started_at);
  const startStr = start.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });

  if (!run.completed_at) return `${startStr} - ongoing`;

  const end = new Date(run.completed_at);
  const endStr = end.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });

  return `${startStr} - ${endStr}`;
}
```

### 3. Shared Type Definitions

```typescript
// File: /dashboard/src/types/unified-view.ts

import type { Session, Run, SessionEvent } from './index';

export interface SessionWithRuns extends Session {
  runs: Run[];
  childSessions?: SessionWithRuns[];
}

export interface RunWithSession extends Run {
  session: Session | null;
}

export interface UnifiedViewSelection {
  selectedRunId: string | null;
  selectedSessionId: string | null;
}

export type UnifiedViewTab =
  | 'session-timeline'
  | 'run-centric'
  | 'tree-view'
  | 'swimlane'
  | 'activity-feed'
  | 'dashboard-cards';

export interface UnifiedViewTabConfig {
  id: UnifiedViewTab;
  label: string;
  icon: string;
  description: string;
}

export const UNIFIED_VIEW_TABS: UnifiedViewTabConfig[] = [
  { id: 'session-timeline', label: 'Session Timeline', icon: 'Layers', description: 'Sessions with run blocks' },
  { id: 'run-centric', label: 'Run Centric', icon: 'Zap', description: 'Runs with session context' },
  { id: 'tree-view', label: 'Tree View', icon: 'GitBranch', description: 'Hierarchical tree' },
  { id: 'swimlane', label: 'Swimlane', icon: 'GanttChart', description: 'Timeline swimlanes' },
  { id: 'activity-feed', label: 'Activity Feed', icon: 'Activity', description: 'Chronological feed' },
  { id: 'dashboard-cards', label: 'Dashboard', icon: 'LayoutGrid', description: 'Card overview' },
];
```

## Tab-Specific Components

### 1. RunCentricTab (Main Container)

```typescript
// File: /dashboard/src/components/features/unified-view/tabs/RunCentricTab.tsx

import { useState, useCallback } from 'react';
import { useSessionsWithRuns } from '@/hooks/useSessionsWithRuns';
import { useSessionEvents } from '@/hooks/useSessions';
import { RunListPanel } from './run-centric/RunListPanel';
import { SessionContextPanel } from './run-centric/SessionContextPanel';
import { RunEventsStream } from './run-centric/RunEventsStream';
import { filterEventsByRun } from '@/utils/runTimeFilter';
import type { Run, RunStatus } from '@/types';
import { RefreshCw, Filter, Zap } from 'lucide-react';

export function RunCentricTab() {
  const { runs, sessions, loading, error, refresh } = useSessionsWithRuns();
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [statusFilter, setStatusFilter] = useState<RunStatus | 'all'>('all');

  const selectedSession = selectedRun
    ? sessions.find(s => s.session_id === selectedRun.session_id) || null
    : null;

  const { events: sessionEvents, loading: eventsLoading } = useSessionEvents(
    selectedRun?.session_id || null
  );

  const runEvents = selectedRun
    ? filterEventsByRun(sessionEvents, selectedRun)
    : [];

  const handleSelectRun = useCallback((run: Run) => {
    setSelectedRun(run);
  }, []);

  const handleSelectRunFromHistory = useCallback((runId: string) => {
    const run = runs.find(r => r.run_id === runId);
    if (run) setSelectedRun(run);
  }, [runs]);

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 px-4 py-3 bg-white border-b border-gray-200 flex-shrink-0">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Run-Centric View</h2>
          <p className="text-sm text-gray-500">
            {runs.length} runs across {sessions.length} sessions
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as RunStatus | 'all')}
              className="text-sm border border-gray-300 rounded-md px-2 py-1.5"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Two-Panel Layout */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Run List */}
        <div className="w-96 border-r border-gray-200 bg-white flex-shrink-0">
          <RunListPanel
            runs={runs}
            selectedRunId={selectedRun?.run_id || null}
            onSelectRun={handleSelectRun}
            statusFilter={statusFilter}
            loading={loading}
          />
        </div>

        {/* Right: Context Panel */}
        <div className="flex-1 flex flex-col min-w-0 bg-gray-50">
          {selectedRun ? (
            <>
              <div className="flex-shrink-0 border-b border-gray-200 bg-white">
                <SessionContextPanel
                  session={selectedSession}
                  runs={selectedSession?.runs || []}
                  selectedRunId={selectedRun.run_id}
                  onSelectRun={handleSelectRunFromHistory}
                />
              </div>

              <div className="flex-1 min-h-0 overflow-hidden">
                <RunEventsStream
                  run={selectedRun}
                  events={runEvents}
                  loading={eventsLoading}
                  isRunning={selectedRun.status === 'running'}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <Zap className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                <p className="text-lg font-medium">Select a run</p>
                <p className="text-sm mt-1">
                  Choose a run from the list to view session context and events
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

### 2. RunListPanel Component

```typescript
// File: /dashboard/src/components/features/unified-view/tabs/run-centric/RunListPanel.tsx

import { useMemo, useState } from 'react';
import type { Run, RunStatus } from '@/types';
import type { RunWithSession } from '@/types/unified-view';
import { RunStatusBadge } from '@/components/features/runs/RunStatusBadge';
import { Badge, CopyButton, EmptyState, SkeletonCard } from '@/components/common';
import { formatRelativeTime } from '@/utils/formatters';
import { Search, Zap, Clock, GitBranch } from 'lucide-react';

interface RunListPanelProps {
  runs: RunWithSession[];
  selectedRunId: string | null;
  onSelectRun: (run: Run) => void;
  statusFilter: RunStatus | 'all';
  loading?: boolean;
}

function formatDuration(startTime: string | null, endTime: string | null): string {
  if (!startTime) return 'queued';
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const diffMs = end.getTime() - start.getTime();

  if (diffMs < 1000) return '<1s';
  if (diffMs < 60000) return `${Math.floor(diffMs / 1000)}s`;
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.floor((diffMs % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

export function RunListPanel({
  runs,
  selectedRunId,
  onSelectRun,
  statusFilter,
  loading = false,
}: RunListPanelProps) {
  const [search, setSearch] = useState('');

  const filteredRuns = useMemo(() => {
    let result = [...runs];

    if (statusFilter !== 'all') {
      result = result.filter(r => r.status === statusFilter);
    }

    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter(r =>
        r.run_id.toLowerCase().includes(searchLower) ||
        r.session_id.toLowerCase().includes(searchLower) ||
        r.agent_name?.toLowerCase().includes(searchLower)
      );
    }

    result.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    return result;
  }, [runs, statusFilter, search]);

  if (loading && runs.length === 0) {
    return (
      <div className="p-4 space-y-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-200">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search runs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredRuns.length === 0 ? (
          <EmptyState
            icon={<Zap className="w-12 h-12" />}
            title="No runs found"
            description={search ? 'Try adjusting your search' : 'Runs will appear here'}
          />
        ) : (
          filteredRuns.map(run => (
            <RunListItem
              key={run.run_id}
              run={run}
              isSelected={run.run_id === selectedRunId}
              onSelect={() => onSelectRun(run)}
            />
          ))
        )}
      </div>

      <div className="px-3 py-2 border-t border-gray-200 text-xs text-gray-500">
        {filteredRuns.length} of {runs.length} runs
      </div>
    </div>
  );
}

interface RunListItemProps {
  run: RunWithSession;
  isSelected: boolean;
  onSelect: () => void;
}

function RunListItem({ run, isSelected, onSelect }: RunListItemProps) {
  const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);
  const sessionName = run.session?.agent_name || run.agent_name || run.session_id.slice(0, 12);

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 rounded-lg border transition-all ${
        isSelected
          ? 'border-primary-500 bg-primary-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <RunStatusBadge status={run.status} />
        <div className="flex items-center gap-1">
          <span className="font-mono text-xs text-gray-500">
            {run.run_id.slice(0, 8)}
          </span>
          <CopyButton text={run.run_id} />
        </div>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-medium text-gray-900 truncate">
          {sessionName}
        </span>
        <Badge
          variant={run.type === 'start_session' ? 'info' : 'default'}
          size="sm"
        >
          {run.type === 'start_session' ? 'start' : 'resume'}
        </Badge>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDuration(run.started_at, run.completed_at)}
            {isActive && (
              <span className="relative flex h-1.5 w-1.5 ml-1">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
              </span>
            )}
          </span>
          {run.parent_session_id && (
            <span className="flex items-center gap-1">
              <GitBranch className="w-3 h-3" />
              child
            </span>
          )}
        </div>
        <span>{formatRelativeTime(run.created_at)}</span>
      </div>
    </button>
  );
}
```

### 3. SessionContextPanel Component

```typescript
// File: /dashboard/src/components/features/unified-view/tabs/run-centric/SessionContextPanel.tsx

import { useMemo } from 'react';
import type { Session, Run } from '@/types';
import type { SessionWithRuns } from '@/types/unified-view';
import { StatusBadge, CopyButton, Badge } from '@/components/common';
import { formatRelativeTime, formatDuration } from '@/utils/formatters';
import { Bot, Folder, Clock, GitBranch, ExternalLink, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

interface SessionContextPanelProps {
  session: SessionWithRuns | null;
  runs: Run[];
  selectedRunId: string;
  onSelectRun: (runId: string) => void;
}

export function SessionContextPanel({
  session,
  runs,
  selectedRunId,
  onSelectRun,
}: SessionContextPanelProps) {
  if (!session) {
    return (
      <div className="p-4 text-center text-gray-500">
        Session not found
      </div>
    );
  }

  const sessionDuration = useMemo(() => {
    const start = new Date(session.created_at).getTime();
    const end = session.modified_at
      ? new Date(session.modified_at).getTime()
      : Date.now();
    return formatDuration(end - start);
  }, [session.created_at, session.modified_at]);

  return (
    <div className="p-4 space-y-4">
      {/* Session Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-semibold text-gray-900">
              {session.agent_name || session.session_id.slice(0, 16)}
            </h3>
            <StatusBadge status={session.status} />
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <span className="font-mono">{session.session_id.slice(0, 12)}...</span>
            <CopyButton text={session.session_id} />
            <Link
              to={`/sessions?id=${session.session_id}`}
              className="ml-1 text-primary-600 hover:text-primary-700"
            >
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        <div className="text-right text-sm text-gray-500">
          <div className="flex items-center gap-1.5 justify-end">
            <Clock className="w-4 h-4" />
            {sessionDuration}
          </div>
          <div className="text-xs mt-0.5">
            {formatRelativeTime(session.created_at)}
          </div>
        </div>
      </div>

      {/* Session Metadata */}
      <div className="flex items-center gap-4 text-sm">
        {session.agent_name && (
          <div className="flex items-center gap-1.5 text-gray-600">
            <Bot className="w-4 h-4 text-gray-400" />
            {session.agent_name}
          </div>
        )}
        {session.project_dir && (
          <div className="flex items-center gap-1.5 text-gray-500">
            <Folder className="w-4 h-4 text-gray-400" />
            <span className="truncate max-w-[180px]" title={session.project_dir}>
              {session.project_dir.split('/').pop()}
            </span>
          </div>
        )}
        {session.parent_session_id && (
          <div className="flex items-center gap-1.5 text-gray-500">
            <GitBranch className="w-4 h-4 text-gray-400" />
            <span className="font-mono text-xs">
              Parent: {session.parent_session_id.slice(0, 8)}
            </span>
          </div>
        )}
      </div>

      {/* Run History (compact chips) */}
      <div>
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
          Run History ({runs.length})
        </h4>
        <div className="flex flex-wrap gap-1.5">
          {runs.map((run, index) => (
            <RunHistoryChip
              key={run.run_id}
              run={run}
              index={index + 1}
              isSelected={run.run_id === selectedRunId}
              onClick={() => onSelectRun(run.run_id)}
            />
          ))}
        </div>
      </div>

      {/* Child Sessions */}
      {session.childSessions && session.childSessions.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Child Sessions ({session.childSessions.length})
          </h4>
          <div className="space-y-1.5">
            {session.childSessions.map(child => (
              <ChildSessionRow key={child.session_id} session={child} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RunHistoryChip({ run, index, isSelected, onClick }) {
  const statusColors = {
    pending: 'bg-gray-100 text-gray-700',
    claimed: 'bg-blue-100 text-blue-700',
    running: 'bg-emerald-100 text-emerald-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    stopped: 'bg-gray-100 text-gray-600',
  };

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full transition-all ${
        isSelected ? 'ring-2 ring-primary-500 ring-offset-1' : 'hover:ring-1 hover:ring-gray-300'
      } ${statusColors[run.status] || statusColors.pending}`}
    >
      #{index}
      <span className="text-[10px] opacity-75">
        {run.type === 'start_session' ? 'start' : 'resume'}
      </span>
    </button>
  );
}

function ChildSessionRow({ session }) {
  return (
    <Link
      to={`/sessions?id=${session.session_id}`}
      className="flex items-center justify-between p-2 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors group"
    >
      <div className="flex items-center gap-2">
        <GitBranch className="w-3.5 h-3.5 text-gray-400" />
        <span className="text-sm text-gray-700">
          {session.agent_name || session.session_id.slice(0, 12)}
        </span>
        <StatusBadge status={session.status} />
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">{session.runs.length} runs</span>
        <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
      </div>
    </Link>
  );
}
```

### 4. RunEventsStream Component

```typescript
// File: /dashboard/src/components/features/unified-view/tabs/run-centric/RunEventsStream.tsx

import type { Run, SessionEvent } from '@/types';
import { EventTimeline } from '@/components/features/sessions/EventTimeline';
import { formatRunTimeRange } from '@/utils/runTimeFilter';
import { Badge, EmptyState } from '@/components/common';
import { Clock, Zap, AlertTriangle } from 'lucide-react';

interface RunEventsStreamProps {
  run: Run;
  events: SessionEvent[];
  loading?: boolean;
  isRunning?: boolean;
}

export function RunEventsStream({
  run,
  events,
  loading = false,
  isRunning = false,
}: RunEventsStreamProps) {
  const timeRange = formatRunTimeRange(run);

  if (!run.started_at) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-gray-500">
        <Clock className="w-12 h-12 text-gray-300 mb-4" />
        <p className="text-lg font-medium">Run hasn't started yet</p>
        <p className="text-sm mt-1">Waiting for runner to claim and start</p>
        <div className="mt-4">
          <Badge variant="default">Status: {run.status}</Badge>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Run context header */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Zap className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-900">Run Events</span>
          </div>
          <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
            {run.type === 'start_session' ? 'start' : 'resume'}
          </Badge>
        </div>

        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">
            <Clock className="w-3.5 h-3.5 inline mr-1" />
            {timeRange}
          </span>
          <span className="text-gray-500">{events.length} events</span>
        </div>
      </div>

      {/* Error banner if run failed */}
      {run.error && (
        <div className="flex-shrink-0 px-4 py-2 bg-red-50 border-b border-red-200">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Run Failed</p>
              <p className="text-xs text-red-600 mt-0.5">{run.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Events timeline */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {events.length === 0 && !loading ? (
          <div className="h-full flex items-center justify-center p-8">
            <EmptyState
              title="No events yet"
              description={isRunning ? "Events will appear as the agent runs" : "No events recorded"}
            />
          </div>
        ) : (
          <EventTimeline
            events={events}
            loading={loading}
            isRunning={isRunning}
          />
        )}
      </div>
    </div>
  );
}
```

## File Structure

```
dashboard/src/
├── components/
│   └── features/
│       └── unified-view/
│           ├── index.ts
│           ├── UnifiedViewPage.tsx
│           ├── TabNavigation.tsx
│           └── tabs/
│               ├── index.ts
│               ├── RunCentricTab.tsx
│               └── run-centric/
│                   ├── index.ts
│                   ├── RunListPanel.tsx
│                   ├── SessionContextPanel.tsx
│                   └── RunEventsStream.tsx
├── hooks/
│   └── useSessionsWithRuns.ts
├── types/
│   └── unified-view.ts
├── utils/
│   └── runTimeFilter.ts
└── pages/
    └── UnifiedView.tsx
```

## Data Flow

```
1. Page Mount
   └── UnifiedViewPage renders with default tab
       └── useSessionsWithRuns() hook activates
           ├── useSessions() context provides sessions via SSE
           └── runService.getRuns() fetches runs
               └── Joins data into RunWithSession[]

2. User Selects a Run
   └── RunListPanel.onSelectRun(run)
       └── setSelectedRun(run)
           ├── SessionContextPanel receives session context
           └── useSessionEvents(run.session_id) activates
               └── filterEventsByRun() filters to time window
                   └── RunEventsStream renders filtered events

3. Real-time Updates
   ├── SSE delivers new events → Events auto-filtered
   └── Auto-refresh interval (5s) → Runs list updates
```

## Step-by-Step Implementation Order

1. **Create shared types** (`types/unified-view.ts`)
2. **Create utility functions** (`utils/runTimeFilter.ts`)
3. **Create shared hook** (`hooks/useSessionsWithRuns.ts`)
4. **Create tab navigation** (`components/features/unified-view/TabNavigation.tsx`)
5. **Create unified view page** (`components/features/unified-view/UnifiedViewPage.tsx`)
6. **Create RunListPanel** (`tabs/run-centric/RunListPanel.tsx`)
7. **Create SessionContextPanel** (`tabs/run-centric/SessionContextPanel.tsx`)
8. **Create RunEventsStream** (`tabs/run-centric/RunEventsStream.tsx`)
9. **Create RunCentricTab** (`tabs/RunCentricTab.tsx`)
10. **Add route** (update `router.tsx`)
11. **Add sidebar link** (update `layout/Sidebar.tsx`)

## Integration Notes

- Reuses existing `RunStatusBadge` from `components/features/runs/`
- Reuses existing `EventTimeline` from `components/features/sessions/`
- Follows existing Tailwind styling patterns
- Uses existing formatters from `utils/formatters.ts`
- Integrates with existing SSE context for real-time updates
