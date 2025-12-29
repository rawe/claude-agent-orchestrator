# Approach 1: Session-Centric Timeline with Run Blocks

## Status

**Implementation Guide** - Ready for Development

## Overview

This approach shows **sessions as the primary entity** with runs visualized as embedded "execution blocks" within the session timeline. Events are grouped under their respective runs through timestamp correlation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Session: orchestrator-main                                              │
│ Status: finished │ Agent: orchestrator │ Created: 2h ago                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ Run #1 (start_session) ─────────────────────────────────────────┐   │
│  │ Started: 2h ago  │ Duration: 5m 23s  │ Runner: runner-abc        │   │
│  │ Prompt: "Orchestrate the data pipeline..."                       │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  ○ session_start                                    10:00:00     │   │
│  │  ○ tool_call: start_agent_session (child-1)        10:00:45     │   │
│  │  ○ assistant: "Started 2 child agents..."          10:01:02     │   │
│  │  ○ session_stop                                     10:05:23     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─ Run #2 (resume_session) ────────────────────────────────────────┐   │
│  │ Started: 1h 30m ago  │ Duration: 2m 15s  │ Trigger: callback     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Diagram

```
UnifiedViewPage
  │
  ├── TabNavigation (shared across all 6 approaches)
  │
  └── SessionTimelineTab
        │
        ├── SessionListWithRuns (left sidebar)
        │     ├── SessionCardWithRuns
        │     └── RunCountBadge
        │
        └── SessionTimelineView (main content)
              ├── SessionHeader
              └── RunBlock (repeated for each run)
                    ├── RunBlockHeader
                    ├── PromptSection (collapsible)
                    └── EventsTimeline
                          └── EventCard (existing component)
```

## Shared Infrastructure

### 1. Combined Types (`/dashboard/src/types/unified.ts`)

```typescript
import type { Session, Run, SessionEvent } from './index';

export interface SessionWithRuns {
  session: Session;
  runs: Run[];
  events: SessionEvent[];
  eventsByRun: Map<string, SessionEvent[]>;
  orphanedEvents: SessionEvent[];
  runCount: number;
  latestRunStatus: Run['status'] | null;
  isActive: boolean;
}

export interface RunWithEvents {
  run: Run;
  events: SessionEvent[];
  runNumber: number;
}
```

### 2. Event-to-Run Correlation Utility (`/dashboard/src/utils/sessionRunUtils.ts`)

```typescript
import type { Run, SessionEvent } from '@/types';

export function correlateEventsWithRuns(
  events: SessionEvent[],
  runs: Run[]
): Map<string, SessionEvent[]> {
  const eventsByRun = new Map<string, SessionEvent[]>();

  runs.forEach(run => {
    eventsByRun.set(run.run_id, []);
  });

  const sortedRuns = [...runs].sort((a, b) => {
    if (!a.started_at) return 1;
    if (!b.started_at) return -1;
    return new Date(a.started_at).getTime() - new Date(b.started_at).getTime();
  });

  events.forEach(event => {
    const eventTime = new Date(event.timestamp).getTime();

    const matchingRun = sortedRuns.find(run => {
      if (!run.started_at) return false;
      const startTime = new Date(run.started_at).getTime();

      if (run.completed_at) {
        const endTime = new Date(run.completed_at).getTime();
        return eventTime >= startTime && eventTime <= endTime;
      }

      const activeStatuses = ['running', 'stopping', 'claimed'];
      if (activeStatuses.includes(run.status)) {
        return eventTime >= startTime;
      }

      return false;
    });

    if (matchingRun) {
      eventsByRun.get(matchingRun.run_id)?.push(event);
    }
  });

  return eventsByRun;
}

export function buildRunsWithEvents(
  runs: Run[],
  eventsByRun: Map<string, SessionEvent[]>
): RunWithEvents[] {
  const sortedRuns = [...runs].sort((a, b) => {
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
  });

  return sortedRuns.map((run, index) => ({
    run,
    events: eventsByRun.get(run.run_id) || [],
    runNumber: index + 1,
  }));
}

export function calculateRunGap(
  previousRun: Run | null,
  currentRun: Run
): number | null {
  if (!previousRun?.completed_at || !currentRun.created_at) {
    return null;
  }

  const prevEnd = new Date(previousRun.completed_at).getTime();
  const currStart = new Date(currentRun.created_at).getTime();

  return currStart - prevEnd;
}
```

### 3. Combined Data Hook (`/dashboard/src/hooks/useSessionWithRuns.ts`)

```typescript
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSessions } from '@/contexts';
import { runService } from '@/services';
import { useSessionEvents } from './useSessions';
import { correlateEventsWithRuns } from '@/utils/sessionRunUtils';
import type { Run, SessionWithRuns } from '@/types';

export function useSessionWithRuns(
  sessionId: string | null,
  options: { runsRefreshInterval?: number } = {}
) {
  const { runsRefreshInterval = 5000 } = options;

  const { sessions } = useSessions();
  const { events, loading: eventsLoading } = useSessionEvents(sessionId);

  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [runsError, setRunsError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    if (!sessionId) {
      setRuns([]);
      return;
    }

    setRunsLoading(true);
    try {
      const allRuns = await runService.getRuns();
      const sessionRuns = allRuns.filter(run => run.session_id === sessionId);
      setRuns(sessionRuns);
      setRunsError(null);
    } catch (err) {
      setRunsError(err instanceof Error ? err.message : 'Failed to fetch runs');
    } finally {
      setRunsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (runsRefreshInterval <= 0) return;
    const interval = setInterval(fetchRuns, runsRefreshInterval);
    return () => clearInterval(interval);
  }, [fetchRuns, runsRefreshInterval]);

  const data = useMemo((): SessionWithRuns | null => {
    if (!sessionId) return null;

    const session = sessions.find(s => s.session_id === sessionId);
    if (!session) return null;

    const eventsByRun = correlateEventsWithRuns(events, runs);
    const orphanedEvents = events.filter(event => {
      for (const runEvents of eventsByRun.values()) {
        if (runEvents.includes(event)) return false;
      }
      return true;
    });

    const isActive = runs.some(run =>
      ['pending', 'claimed', 'running', 'stopping'].includes(run.status)
    );

    const latestRun = runs.length > 0
      ? runs.reduce((latest, run) =>
          new Date(run.created_at) > new Date(latest.created_at) ? run : latest
        )
      : null;

    return {
      session,
      runs,
      events,
      eventsByRun,
      orphanedEvents,
      runCount: runs.length,
      latestRunStatus: latestRun?.status ?? null,
      isActive,
    };
  }, [sessionId, sessions, runs, events]);

  return {
    data,
    loading: runsLoading || eventsLoading,
    error: runsError,
    refreshRuns: fetchRuns,
  };
}
```

## Tab-Specific Components

### 1. SessionTimelineTab (`/dashboard/src/components/features/unified/SessionTimelineTab.tsx`)

```typescript
import { useState } from 'react';
import { useSessionWithRuns, useSessionsWithRunCounts } from '@/hooks/useSessionWithRuns';
import { useSessions } from '@/contexts';
import { SessionTimelineView } from './SessionTimelineView';
import { SessionListWithRuns } from './SessionListWithRuns';
import { EmptyState, LoadingState } from '@/components/common';
import { Layers, PanelLeftClose, PanelLeft } from 'lucide-react';

export function SessionTimelineTab() {
  const { sessions, loading: sessionsLoading } = useSessions();
  const { runsBySession, loading: runsLoading } = useSessionsWithRunCounts();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sidebarVisible, setSidebarVisible] = useState(true);

  const { data, loading, error, refreshRuns } = useSessionWithRuns(selectedSessionId, {
    runsRefreshInterval: 5000,
  });

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <div>
          <h2 className="text-base font-semibold text-gray-900">
            Session Timeline with Runs
          </h2>
          <p className="text-sm text-gray-500">
            Sessions as primary entities with embedded run blocks
          </p>
        </div>
      </div>

      <div className="flex-1 flex min-h-0">
        {sidebarVisible && (
          <div className="w-80 border-r border-gray-200 bg-white flex-shrink-0">
            <SessionListWithRuns
              sessions={sessions}
              runsBySession={runsBySession}
              selectedSessionId={selectedSessionId}
              onSelectSession={setSelectedSessionId}
              loading={sessionsLoading || runsLoading}
            />
          </div>
        )}

        <div className="flex-1 bg-gray-50 flex flex-col min-w-0 overflow-hidden">
          <div className="flex-shrink-0 bg-white border-b px-3 py-2">
            <button
              onClick={() => setSidebarVisible(!sidebarVisible)}
              className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              {sidebarVisible ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
              {sidebarVisible ? 'Hide Sessions' : 'Show Sessions'}
            </button>
          </div>

          <div className="flex-1 min-h-0 overflow-hidden">
            {selectedSessionId ? (
              loading ? (
                <LoadingState message="Loading session data..." />
              ) : error ? (
                <div className="p-4 text-red-600">{error}</div>
              ) : data ? (
                <SessionTimelineView data={data} onRefreshRuns={refreshRuns} />
              ) : null
            ) : (
              <div className="h-full flex items-center justify-center">
                <EmptyState
                  icon={<Layers className="w-16 h-16" />}
                  title="Select a session"
                  description="Choose a session from the list to view its timeline with run blocks"
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

### 2. RunBlock Component (`/dashboard/src/components/features/unified/RunBlock.tsx`)

```typescript
import { useState, useEffect } from 'react';
import type { RunWithEvents } from '@/types/unified';
import { RunStatusBadge } from '@/components/features/runs';
import { EventCard } from '@/components/features/sessions';
import { Badge, CopyButton } from '@/components/common';
import { formatRelativeTime, formatDuration } from '@/utils/formatters';
import { ChevronDown, ChevronRight, Play, RotateCcw, Clock, Server, MessageSquare } from 'lucide-react';

interface RunBlockProps {
  runWithEvents: RunWithEvents;
  defaultExpanded?: boolean;
}

export function RunBlock({ runWithEvents, defaultExpanded = true }: RunBlockProps) {
  const { run, events, runNumber } = runWithEvents;
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [eventsExpanded, setEventsExpanded] = useState(true);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    setExpanded(defaultExpanded);
  }, [defaultExpanded]);

  const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);
  const RunTypeIcon = run.type === 'start_session' ? Play : RotateCcw;

  const getRunDuration = () => {
    if (!run.started_at) return '-';
    const start = new Date(run.started_at).getTime();
    const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now();
    return formatDuration(end - start);
  };

  return (
    <div className={`bg-white rounded-lg shadow-sm border overflow-hidden ${
      isActive ? 'border-emerald-300 ring-1 ring-emerald-100' : 'border-gray-200'
    }`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
      >
        <div className="text-gray-400">
          {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        </div>

        <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          run.type === 'start_session' ? 'bg-blue-100' : 'bg-amber-100'
        }`}>
          <RunTypeIcon className={`w-4 h-4 ${
            run.type === 'start_session' ? 'text-blue-600' : 'text-amber-600'
          }`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">Run #{runNumber}</span>
            <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
              {run.type === 'start_session' ? 'start' : 'resume'}
            </Badge>
            <RunStatusBadge status={run.status} />
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {getRunDuration()}
            </span>
            {run.runner_id && (
              <span className="flex items-center gap-1">
                <Server className="w-3 h-3" />
                {run.runner_id.slice(0, 12)}...
              </span>
            )}
            <span>{formatRelativeTime(run.created_at)}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <MessageSquare className="w-3.5 h-3.5" />
          {events.length} events
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <button
              onClick={() => setShowPrompt(!showPrompt)}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
            >
              <ChevronRight className={`w-4 h-4 transition-transform ${showPrompt ? 'rotate-90' : ''}`} />
              <span className="font-medium">Prompt</span>
            </button>
            {showPrompt && (
              <div className="mt-2 p-3 bg-white rounded border border-gray-200">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                  {run.prompt}
                </pre>
              </div>
            )}
          </div>

          <div className="px-4 py-3">
            <button
              onClick={() => setEventsExpanded(!eventsExpanded)}
              className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3"
            >
              <ChevronRight className={`w-4 h-4 transition-transform ${eventsExpanded ? 'rotate-90' : ''}`} />
              Events Timeline
            </button>

            {eventsExpanded && (
              <div className="space-y-2 pl-4 border-l-2 border-gray-200">
                {events.length === 0 ? (
                  <p className="text-sm text-gray-500 italic py-2">No events for this run</p>
                ) : (
                  events.map(event => (
                    <EventCard key={`${event.session_id}-${event.timestamp}`} event={event} />
                  ))
                )}
              </div>
            )}
          </div>

          <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
            <span className="font-mono">{run.run_id.slice(0, 12)}...</span>
            <CopyButton text={run.run_id} />
            {run.error && <span className="text-red-600">Error: {run.error.slice(0, 50)}...</span>}
          </div>
        </div>
      )}
    </div>
  );
}
```

## File Structure

```
dashboard/src/
├── types/
│   ├── index.ts                    # Add: export * from './unified'
│   └── unified.ts                  # SessionWithRuns, RunWithEvents
│
├── utils/
│   ├── index.ts                    # Add: export * from './sessionRunUtils'
│   └── sessionRunUtils.ts          # correlateEventsWithRuns, etc.
│
├── hooks/
│   ├── index.ts                    # Add: export * from './useSessionWithRuns'
│   └── useSessionWithRuns.ts       # Combined data hook
│
├── components/
│   └── features/
│       └── unified/
│           ├── index.ts
│           ├── TabNavigation.tsx
│           ├── SessionTimelineTab.tsx
│           ├── SessionListWithRuns.tsx
│           ├── SessionCardWithRuns.tsx
│           ├── SessionTimelineView.tsx
│           └── RunBlock.tsx
│
└── pages/
    └── UnifiedView.tsx             # Tab container page
```

## Step-by-Step Implementation Order

1. **Create shared types** (`types/unified.ts`)
2. **Create utility functions** (`utils/sessionRunUtils.ts`)
3. **Create combined data hook** (`hooks/useSessionWithRuns.ts`)
4. **Create tab navigation** (`components/features/unified/TabNavigation.tsx`)
5. **Create unified view page** (`components/features/unified/UnifiedViewPage.tsx`)
6. **Create SessionCardWithRuns** component
7. **Create SessionListWithRuns** component
8. **Create RunBlock** component (reuses existing EventCard)
9. **Create SessionTimelineView** component
10. **Create SessionTimelineTab** component
11. **Add route to router.tsx** (`/unified`)
12. **Add sidebar link** in `layout/Sidebar.tsx`

## Integration Notes

- Reuses existing `EventCard` from `components/features/sessions/`
- Reuses existing `SessionHeader` for session metadata display
- Reuses existing `StatusBadge`, `RunStatusBadge`, `CopyButton`, `Badge`
- Follows existing Tailwind styling patterns
- Uses existing SSE subscription for real-time session updates
- Runs are polled every 5 seconds for active sessions
