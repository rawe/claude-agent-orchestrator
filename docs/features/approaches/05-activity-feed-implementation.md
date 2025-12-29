# Approach 5: Unified Activity Feed

## Status

**Implementation Guide** - Ready for Development

## Overview

A **single chronological feed** mixing run lifecycle events and session events. Similar to a social media activity log, ideal for real-time monitoring.

## Visual Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Activity Feed                               [Filter ▼] [Session ▼]      │
├─────────────────────────────────────────────────────────────────────────┤
│ ● Live updates streaming...                                             │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🚀 RUN STARTED                                            10:45:00 │ │
│ │ Run #3 of orchestrator-main (resume_session)                       │ │
│ │ Prompt: "## Child Result\nchild-1 completed..."                    │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 🔧 EVENT                                                  10:45:15 │ │
│ │ orchestrator-main → tool_call: get_agent_session_result            │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ ✅ RUN COMPLETED                                          10:47:15 │ │
│ │ Run #3 of orchestrator-main │ Duration: 2m 15s                     │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ ❌ RUN FAILED                                             10:42:30 │ │
│ │ Run #1 of child-3 │ Error: "Agent blueprint not found"             │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Diagram

```
ActivityFeedTab
  │
  ├── FeedToolbar
  │     ├── Activity Type Filter Chips
  │     ├── Session Dropdown
  │     ├── Errors Only Toggle
  │     ├── Live Toggle
  │     └── Refresh Button
  │
  ├── ActivityFeed (virtualized list)
  │     └── ActivityCard (polymorphic)
  │           ├── RunActivityCard
  │           └── EventActivityCard
  │
  └── FeedFooter
        ├── Count
        └── Live Indicator
```

## Shared Infrastructure

### 1. Activity Types (`/dashboard/src/types/unified.ts`)

```typescript
import type { Run, SessionEvent } from './index';

export type ActivityType =
  | 'run_started'
  | 'run_completed'
  | 'run_failed'
  | 'run_stopped'
  | 'session_event';

export interface BaseActivityItem {
  id: string;
  timestamp: string;
  type: ActivityType;
  sessionId: string;
}

export interface RunActivityItem extends BaseActivityItem {
  type: 'run_started' | 'run_completed' | 'run_failed' | 'run_stopped';
  run: Run;
  runNumber?: number;
}

export interface EventActivityItem extends BaseActivityItem {
  type: 'session_event';
  event: SessionEvent;
  runId?: string;
}

export type ActivityItem = RunActivityItem | EventActivityItem;

export interface ActivityFilters {
  activityTypes: ActivityType[];
  sessionId?: string;
  errorsOnly: boolean;
}
```

### 2. Unified Activity Hook (`/dashboard/src/hooks/useUnifiedActivity.ts`)

```typescript
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSSE, useSessions } from '@/contexts';
import { runService, sessionService } from '@/services';
import type { ActivityItem, RunActivityItem, EventActivityItem, ActivityFilters } from '@/types/unified';
import type { Run, SessionEvent } from '@/types';

const DEFAULT_PAGE_SIZE = 50;

export function useUnifiedActivity(options: { filters?: ActivityFilters } = {}) {
  const { filters } = options;
  const { subscribe } = useSSE();
  const { sessions } = useSessions();

  const [runs, setRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(true);
  const [visibleCount, setVisibleCount] = useState(DEFAULT_PAGE_SIZE);

  // Fetch initial data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const runsData = await runService.getRuns();
      setRuns(runsData);

      // Fetch events for all sessions
      const allEvents: SessionEvent[] = [];
      const targetSessions = filters?.sessionId
        ? sessions.filter(s => s.session_id === filters.sessionId)
        : sessions;

      await Promise.all(
        targetSessions.map(async session => {
          try {
            const sessionEvents = await sessionService.getSessionEvents(session.session_id);
            allEvents.push(...sessionEvents);
          } catch (e) { /* ignore */ }
        })
      );

      setEvents(allEvents);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch activity');
    } finally {
      setLoading(false);
    }
  }, [sessions, filters?.sessionId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // SSE subscription for live updates
  useEffect(() => {
    if (!isLive) return;

    const handleMessage = (message: any) => {
      if (message.type === 'event' && message.data) {
        if (filters?.sessionId && message.data.session_id !== filters.sessionId) return;

        setEvents(prev => {
          const key = `${message.data.session_id}-${message.data.timestamp}`;
          if (prev.some(e => `${e.session_id}-${e.timestamp}` === key)) return prev;
          return [message.data, ...prev];
        });
      }

      if (message.type === 'run_failed' || message.type === 'session_updated') {
        runService.getRuns().then(setRuns).catch(console.error);
      }
    };

    return subscribe(handleMessage);
  }, [subscribe, isLive, filters?.sessionId]);

  // Build run number map
  const runNumbersMap = useMemo(() => {
    const map = new Map<string, number>();
    const bySession = new Map<string, Run[]>();

    runs.forEach(run => {
      const list = bySession.get(run.session_id) || [];
      list.push(run);
      bySession.set(run.session_id, list);
    });

    bySession.forEach(sessionRuns => {
      sessionRuns.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      sessionRuns.forEach((run, i) => map.set(run.run_id, i + 1));
    });

    return map;
  }, [runs]);

  // Convert to activity items
  const runActivities: RunActivityItem[] = useMemo(() => {
    return runs.flatMap(run => {
      const items: RunActivityItem[] = [];
      const runNumber = runNumbersMap.get(run.run_id);

      if (run.started_at) {
        items.push({
          id: `run-started-${run.run_id}`,
          timestamp: run.started_at,
          type: 'run_started',
          sessionId: run.session_id,
          run,
          runNumber,
        });
      }

      if (run.completed_at) {
        const type = run.status === 'failed' ? 'run_failed'
          : run.status === 'stopped' ? 'run_stopped'
          : 'run_completed';
        items.push({
          id: `run-${type}-${run.run_id}`,
          timestamp: run.completed_at,
          type,
          sessionId: run.session_id,
          run,
          runNumber,
        });
      }

      return items;
    });
  }, [runs, runNumbersMap]);

  const eventActivities: EventActivityItem[] = useMemo(() => {
    return events.map(event => ({
      id: `event-${event.session_id}-${event.timestamp}`,
      timestamp: event.timestamp,
      type: 'session_event' as const,
      sessionId: event.session_id,
      event,
    }));
  }, [events]);

  // Merge, filter, sort
  const allActivities = useMemo(() => {
    let merged: ActivityItem[] = [...runActivities, ...eventActivities];

    if (filters?.activityTypes?.length) {
      merged = merged.filter(a => filters.activityTypes.includes(a.type));
    }
    if (filters?.sessionId) {
      merged = merged.filter(a => a.sessionId === filters.sessionId);
    }
    if (filters?.errorsOnly) {
      merged = merged.filter(a => {
        if (a.type === 'run_failed') return true;
        if (a.type === 'session_event') {
          const evt = (a as EventActivityItem).event;
          return evt.error || (evt.event_type === 'session_stop' && evt.exit_code !== 0);
        }
        return false;
      });
    }

    return merged.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [runActivities, eventActivities, filters]);

  const activities = useMemo(() => allActivities.slice(0, visibleCount), [allActivities, visibleCount]);
  const hasMore = visibleCount < allActivities.length;

  return {
    activities,
    loading,
    error,
    hasMore,
    loadMore: () => setVisibleCount(prev => prev + DEFAULT_PAGE_SIZE),
    refresh: fetchData,
    isLive,
    setIsLive,
  };
}
```

## Tab-Specific Components

### 1. ActivityFeedTab

```typescript
import { useState } from 'react';
import { useUnifiedActivity } from '@/hooks/useUnifiedActivity';
import { ActivityFeed } from './ActivityFeed';
import { FeedToolbar } from './FeedToolbar';
import { FeedFooter } from './FeedFooter';
import { LoadingState, EmptyState } from '@/components/common';
import type { ActivityFilters, ActivityType } from '@/types/unified';

export function ActivityFeedTab() {
  const [filters, setFilters] = useState<ActivityFilters>({
    activityTypes: [],
    errorsOnly: false,
  });

  const {
    activities,
    loading,
    error,
    hasMore,
    loadMore,
    refresh,
    isLive,
    setIsLive,
  } = useUnifiedActivity({ filters });

  const handleToggleType = (type: ActivityType) => {
    setFilters(prev => ({
      ...prev,
      activityTypes: prev.activityTypes.includes(type)
        ? prev.activityTypes.filter(t => t !== type)
        : [...prev.activityTypes, type],
    }));
  };

  if (loading && activities.length === 0) {
    return <LoadingState message="Loading activity feed..." />;
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <FeedToolbar
        filters={filters}
        onFilterChange={setFilters}
        onToggleType={handleToggleType}
        isLive={isLive}
        onToggleLive={() => setIsLive(!isLive)}
        onRefresh={refresh}
      />

      <div className="flex-1 overflow-hidden">
        {activities.length === 0 ? (
          <EmptyState title="No activity found" />
        ) : (
          <ActivityFeed
            activities={activities}
            hasMore={hasMore}
            onLoadMore={loadMore}
            isLive={isLive}
          />
        )}
      </div>

      <FeedFooter visibleCount={activities.length} isLive={isLive} />
    </div>
  );
}
```

### 2. RunActivityCard

```typescript
import type { RunActivityItem } from '@/types/unified';
import { RunStatusBadge } from '@/components/features/runs/RunStatusBadge';
import { Badge, CopyButton } from '@/components/common';
import { formatRelativeTime } from '@/utils/formatters';
import { Zap, CheckCircle2, XCircle, StopCircle, ChevronDown, ChevronRight } from 'lucide-react';

interface RunActivityCardProps {
  activity: RunActivityItem;
  expanded: boolean;
  onToggle: () => void;
}

const TYPE_CONFIG = {
  run_started: { icon: Zap, label: 'RUN STARTED', color: 'blue', emoji: '🚀' },
  run_completed: { icon: CheckCircle2, label: 'RUN COMPLETED', color: 'emerald', emoji: '✅' },
  run_failed: { icon: XCircle, label: 'RUN FAILED', color: 'red', emoji: '❌' },
  run_stopped: { icon: StopCircle, label: 'RUN STOPPED', color: 'gray', emoji: '⏹️' },
};

export function RunActivityCard({ activity, expanded, onToggle }: RunActivityCardProps) {
  const { run, runNumber, type } = activity;
  const config = TYPE_CONFIG[type];
  const Icon = config.icon;

  const formatDuration = () => {
    if (!run.started_at || !run.completed_at) return '-';
    const ms = new Date(run.completed_at).getTime() - new Date(run.started_at).getTime();
    if (ms < 60000) return `${Math.floor(ms / 1000)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  return (
    <div className={`bg-white rounded-lg border border-gray-200 border-l-4 border-l-${config.color}-500 shadow-sm`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
      >
        <div className={`w-8 h-8 rounded-lg bg-${config.color}-100 flex items-center justify-center`}>
          <Icon className={`w-4 h-4 text-${config.color}-600`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-gray-500 uppercase">
              {config.emoji} {config.label}
            </span>
            <span className="text-xs text-gray-400">
              {formatRelativeTime(activity.timestamp)}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-sm font-medium text-gray-900">
              Run #{runNumber} of {run.session_id.slice(0, 12)}...
            </span>
            <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
              {run.type === 'start_session' ? 'start' : 'resume'}
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <RunStatusBadge status={run.status} />
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="mt-3 space-y-3">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Agent:</span>{' '}
                <span className="font-medium">{run.agent_name || '-'}</span>
              </div>
              <div>
                <span className="text-gray-500">Duration:</span>{' '}
                <span className="font-medium">{formatDuration()}</span>
              </div>
            </div>

            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">Prompt</div>
              <div className="bg-gray-50 rounded-lg p-3 max-h-32 overflow-y-auto">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                  {run.prompt.slice(0, 300)}{run.prompt.length > 300 ? '...' : ''}
                </pre>
              </div>
            </div>

            {run.error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-700">{run.error}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
```

### 3. ActivityFeed (with infinite scroll)

```typescript
import { useRef, useEffect } from 'react';
import { ActivityCard } from './ActivityCard';
import type { ActivityItem } from '@/types/unified';
import { Loader2 } from 'lucide-react';

interface ActivityFeedProps {
  activities: ActivityItem[];
  hasMore: boolean;
  onLoadMore: () => void;
  isLive: boolean;
}

export function ActivityFeed({ activities, hasMore, onLoadMore, isLive }: ActivityFeedProps) {
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore) onLoadMore();
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [hasMore, onLoadMore]);

  return (
    <div className="h-full overflow-y-auto px-4 py-4">
      <div className="max-w-3xl mx-auto space-y-3">
        {isLive && (
          <div className="flex items-center justify-center gap-2 py-2 text-sm text-emerald-600">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            Watching for new activity...
          </div>
        )}

        {activities.map((activity, i) => (
          <ActivityCard key={activity.id} activity={activity} animate={isLive && i === 0} />
        ))}

        <div ref={loadMoreRef} className="h-8 flex items-center justify-center">
          {hasMore && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading more...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

## File Structure

```
dashboard/src/
├── types/
│   └── unified.ts              # ActivityItem types
│
├── hooks/
│   └── useUnifiedActivity.ts   # Activity feed hook
│
├── components/
│   └── features/
│       └── unified/
│           ├── ActivityFeedTab.tsx
│           ├── ActivityFeed.tsx
│           ├── ActivityCard.tsx
│           ├── RunActivityCard.tsx
│           ├── EventActivityCard.tsx
│           ├── FeedToolbar.tsx
│           └── FeedFooter.tsx
│
└── pages/
    └── UnifiedView.tsx
```

## Step-by-Step Implementation Order

1. **Create activity types** (`types/unified.ts`)
2. **Create activity hook** (`hooks/useUnifiedActivity.ts`)
3. **Create FeedToolbar** (filters)
4. **Create FeedFooter** (count, live indicator)
5. **Create RunActivityCard** (run lifecycle cards)
6. **Create EventActivityCard** (session event cards)
7. **Create ActivityCard** (polymorphic wrapper)
8. **Create ActivityFeed** (infinite scroll list)
9. **Create ActivityFeedTab** (main component)

## Key Design Decisions

### Real-time Updates
- SSE subscription for new events and run updates
- New items animate in at top when live
- Auto-scroll to new items optional

### Infinite Scroll
- Intersection Observer on sentinel element
- Load 50 items at a time
- Virtualization for 1000+ items (future)

### Activity Types
- Run lifecycle: started, completed, failed, stopped
- Session events: all existing event types
- Discriminated union for type-safe rendering
