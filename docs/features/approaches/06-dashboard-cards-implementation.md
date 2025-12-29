# Approach 6: Dashboard Cards with Drill-Down

## Status

**Implementation Guide** - Ready for Development

## Overview

A **grid/list of session cards** with activity sparklines and run counts. Click any card to open a slide-out detail panel with full session info, runs, and events.

## Visual Design

```
┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐
│ orchestrator-main    │  │ child-1              │  │ child-2         │
│ ━━━━━━━━━━━━━━━━━━━ │  │ ━━━━━━━━━━━━━━━━━━━ │  │ ━━━━━━━━━━━━━━━ │
│ ● FINISHED          │  │ ● FINISHED          │  │ ○ RUNNING       │
│                      │  │                      │  │                 │
│ Agent: orchestrator  │  │ Agent: researcher    │  │ Agent: coder    │
│ Runs: 4 ✓           │  │ Runs: 1 ✓           │  │ Runs: 2 (1 ●)   │
│ Children: 2          │  │ Parent: orch...      │  │ Parent: orch... │
│                      │  │                      │  │                 │
│ ▃▃▃▅▅▅▅▃▃▃▇▇▃▃     │  │ ▃▃▃▃▅▅▅▅▃▃▃        │  │ ▃▃▃▅▅▅▇▇●      │
│ └─ run activity ──┘  │  │ └─ run activity ──┘  │  │ └─ activity ──┘ │
│                      │  │                      │  │                 │
│ Last: 45m ago        │  │ Last: 1h ago         │  │ Active now      │
└──────────────────────┘  └──────────────────────┘  └─────────────────┘
```

## Component Diagram

```
DashboardCardsTab
  │
  ├── TabHeader
  │     ├── Title
  │     ├── Search
  │     ├── Status Filter
  │     ├── Sort Dropdown
  │     ├── Layout Toggle (Grid/List)
  │     └── Refresh
  │
  ├── CardGrid / CardList
  │     └── SessionCardEnhanced (repeated)
  │           ├── Session Header
  │           ├── Agent & Metadata
  │           ├── Run Count Badge
  │           ├── Activity Sparkline
  │           └── Last Activity
  │
  └── SessionDetailPanel (slide-out)
        ├── Overview Tab
        │     ├── Session Metadata
        │     └── Run Statistics
        ├── Runs Tab
        │     └── RunsSection
        └── Events Tab
              └── EventTimeline
```

## Shared Infrastructure

### 1. Types (`/dashboard/src/types/unified.ts`)

```typescript
import type { Session, Run } from './index';

export interface SessionWithRuns extends Session {
  runs: Run[];
  runCount: number;
  activeRunCount: number;
  lastRunAt: string | null;
  childSessionIds: string[];
}

export interface SessionRunStats {
  totalRuns: number;
  completedRuns: number;
  failedRuns: number;
  runningRuns: number;
  pendingRuns: number;
  totalDuration: number;
  averageDuration: number;
}

export interface SparklineDataPoint {
  timestamp: number;
  value: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  runId?: string;
}
```

### 2. Combined Hook (`/dashboard/src/hooks/useSessionsWithRuns.ts`)

```typescript
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useSessions } from '@/contexts';
import { runService } from '@/services';
import type { Run } from '@/types';
import type { SessionWithRuns, SessionRunStats, SparklineDataPoint } from '@/types/unified';

export function useSessionsWithRuns() {
  const { sessions: baseSessions, loading: sessionsLoading } = useSessions();
  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setRunsLoading(true);
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
    const interval = setInterval(fetchRuns, 10000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  // Create runs lookup by session_id
  const runsBySession = useMemo(() => {
    const map = new Map<string, Run[]>();
    runs.forEach(run => {
      const list = map.get(run.session_id) || [];
      list.push(run);
      map.set(run.session_id, list);
    });
    map.forEach(list => {
      list.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    });
    return map;
  }, [runs]);

  // Build child session lookup
  const childSessionsByParent = useMemo(() => {
    const map = new Map<string, string[]>();
    baseSessions.forEach(s => {
      if (s.parent_session_id) {
        const list = map.get(s.parent_session_id) || [];
        list.push(s.session_id);
        map.set(s.parent_session_id, list);
      }
    });
    return map;
  }, [baseSessions]);

  // Merge sessions with runs
  const sessions = useMemo<SessionWithRuns[]>(() => {
    return baseSessions.map(session => {
      const sessionRuns = runsBySession.get(session.session_id) || [];
      const activeRuns = sessionRuns.filter(r =>
        ['pending', 'claimed', 'running', 'stopping'].includes(r.status)
      );
      const lastRun = sessionRuns[sessionRuns.length - 1];

      return {
        ...session,
        runs: sessionRuns,
        runCount: sessionRuns.length,
        activeRunCount: activeRuns.length,
        lastRunAt: lastRun?.created_at || null,
        childSessionIds: childSessionsByParent.get(session.session_id) || [],
      };
    });
  }, [baseSessions, runsBySession, childSessionsByParent]);

  // Get stats for a session
  const getSessionStats = useCallback((sessionId: string): SessionRunStats | null => {
    const sessionRuns = runsBySession.get(sessionId);
    if (!sessionRuns || sessionRuns.length === 0) return null;

    const completed = sessionRuns.filter(r => r.status === 'completed');
    const failed = sessionRuns.filter(r => r.status === 'failed');
    const running = sessionRuns.filter(r => r.status === 'running');
    const pending = sessionRuns.filter(r => ['pending', 'claimed'].includes(r.status));

    const durations = sessionRuns
      .filter(r => r.started_at && r.completed_at)
      .map(r => new Date(r.completed_at!).getTime() - new Date(r.started_at!).getTime());

    const totalDuration = durations.reduce((a, b) => a + b, 0);

    return {
      totalRuns: sessionRuns.length,
      completedRuns: completed.length,
      failedRuns: failed.length,
      runningRuns: running.length,
      pendingRuns: pending.length,
      totalDuration,
      averageDuration: durations.length > 0 ? totalDuration / durations.length : 0,
    };
  }, [runsBySession]);

  // Generate sparkline data for a session
  const getSparklineData = useCallback((sessionId: string): SparklineDataPoint[] => {
    const sessionRuns = runsBySession.get(sessionId);
    if (!sessionRuns || sessionRuns.length === 0) return [];

    return sessionRuns.map(run => ({
      timestamp: new Date(run.created_at).getTime(),
      value: run.completed_at && run.started_at
        ? new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
        : 0,
      status: run.status as SparklineDataPoint['status'],
      runId: run.run_id,
    }));
  }, [runsBySession]);

  return {
    sessions,
    loading: sessionsLoading || runsLoading,
    error,
    refresh: fetchRuns,
    getSessionStats,
    getSparklineData,
  };
}
```

## Tab-Specific Components

### 1. DashboardCardsTab (`/dashboard/src/pages/unified-view/DashboardCardsTab.tsx`)

```typescript
import { useState, useMemo } from 'react';
import { useSessionsWithRuns } from '@/hooks/useSessionsWithRuns';
import { CardGrid } from '@/components/features/unified-view/cards/CardGrid';
import { CardList } from '@/components/features/unified-view/cards/CardList';
import { SessionDetailPanel } from '@/components/features/unified-view/cards/SessionDetailPanel';
import { TabHeader } from '@/components/features/unified-view/cards/TabHeader';
import type { SessionWithRuns } from '@/types/unified';

type LayoutMode = 'grid' | 'list';
type SortField = 'lastActivity' | 'runCount' | 'name' | 'status';
type StatusFilter = 'all' | 'running' | 'finished' | 'failed';

export function DashboardCardsTab() {
  const { sessions, loading, error, refresh, getSessionStats, getSparklineData } = useSessionsWithRuns();

  const [layout, setLayout] = useState<LayoutMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortField, setSortField] = useState<SortField>('lastActivity');
  const [selectedSession, setSelectedSession] = useState<SessionWithRuns | null>(null);

  // Filter and sort sessions
  const filteredSessions = useMemo(() => {
    let result = [...sessions];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(s =>
        s.session_id.toLowerCase().includes(query) ||
        s.agent_name?.toLowerCase().includes(query) ||
        s.description?.toLowerCase().includes(query)
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      result = result.filter(s => {
        if (statusFilter === 'running') return s.activeRunCount > 0;
        if (statusFilter === 'finished') return s.status === 'finished';
        if (statusFilter === 'failed') return s.runs.some(r => r.status === 'failed');
        return true;
      });
    }

    // Sort
    result.sort((a, b) => {
      switch (sortField) {
        case 'lastActivity':
          return (new Date(b.lastRunAt || 0).getTime()) - (new Date(a.lastRunAt || 0).getTime());
        case 'runCount':
          return b.runCount - a.runCount;
        case 'name':
          return (a.agent_name || '').localeCompare(b.agent_name || '');
        case 'status':
          return a.status.localeCompare(b.status);
        default:
          return 0;
      }
    });

    return result;
  }, [sessions, searchQuery, statusFilter, sortField]);

  if (error) {
    return <div className="p-4 text-red-500">Error: {error}</div>;
  }

  const CardComponent = layout === 'grid' ? CardGrid : CardList;

  return (
    <div className="h-full flex flex-col">
      <TabHeader
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        sortField={sortField}
        onSortChange={setSortField}
        layout={layout}
        onLayoutChange={setLayout}
        onRefresh={refresh}
        sessionCount={filteredSessions.length}
      />

      <div className="flex-1 overflow-auto p-4">
        <CardComponent
          sessions={filteredSessions}
          loading={loading}
          onSelectSession={setSelectedSession}
          selectedSessionId={selectedSession?.session_id}
          getSparklineData={getSparklineData}
        />
      </div>

      {selectedSession && (
        <SessionDetailPanel
          session={selectedSession}
          stats={getSessionStats(selectedSession.session_id)}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  );
}
```

### 2. SessionCardEnhanced (`/dashboard/src/components/features/unified-view/cards/SessionCardEnhanced.tsx`)

```typescript
import { useMemo } from 'react';
import { StatusBadge } from '@/components/common';
import { ActivitySparkline } from './ActivitySparkline';
import { formatRelativeTime } from '@/utils/time';
import type { SessionWithRuns, SparklineDataPoint } from '@/types/unified';

interface SessionCardEnhancedProps {
  session: SessionWithRuns;
  isSelected: boolean;
  onClick: () => void;
  sparklineData: SparklineDataPoint[];
  variant?: 'grid' | 'list';
}

export function SessionCardEnhanced({
  session,
  isSelected,
  onClick,
  sparklineData,
  variant = 'grid',
}: SessionCardEnhancedProps) {
  const hasActiveRuns = session.activeRunCount > 0;
  const hasFailed = session.runs.some(r => r.status === 'failed');

  const runSummary = useMemo(() => {
    if (session.runCount === 0) return 'No runs';
    if (hasActiveRuns) return `${session.runCount} runs (${session.activeRunCount} active)`;
    return `${session.runCount} runs`;
  }, [session.runCount, session.activeRunCount, hasActiveRuns]);

  if (variant === 'list') {
    return (
      <div
        className={`flex items-center gap-4 p-4 border rounded-lg cursor-pointer
          transition-all hover:shadow-md hover:border-primary-300
          ${isSelected ? 'border-primary-500 bg-primary-50' : 'border-gray-200 bg-white'}
          ${hasActiveRuns ? 'ring-2 ring-emerald-200' : ''}
        `}
        onClick={onClick}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 truncate">
              {session.session_id.slice(0, 16)}...
            </span>
            <StatusBadge status={session.status} />
            {hasActiveRuns && (
              <span className="flex h-2 w-2">
                <span className="animate-ping absolute h-2 w-2 rounded-full bg-emerald-400 opacity-75" />
                <span className="relative rounded-full h-2 w-2 bg-emerald-500" />
              </span>
            )}
          </div>
          {session.agent_name && (
            <span className="text-sm text-gray-500">{session.agent_name}</span>
          )}
        </div>

        <div className="text-sm text-gray-600">{runSummary}</div>

        <div className="w-32">
          <ActivitySparkline data={sparklineData} height={24} />
        </div>

        <div className="text-sm text-gray-500 w-24 text-right">
          {session.lastRunAt ? formatRelativeTime(session.lastRunAt) : 'Never'}
        </div>
      </div>
    );
  }

  // Grid variant
  return (
    <div
      className={`p-4 border rounded-lg cursor-pointer transition-all
        hover:shadow-lg hover:border-primary-300
        ${isSelected ? 'border-primary-500 bg-primary-50' : 'border-gray-200 bg-white'}
        ${hasActiveRuns ? 'ring-2 ring-emerald-200' : ''}
      `}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-gray-900 truncate">
            {session.session_id.slice(0, 16)}...
          </h3>
          {session.agent_name && (
            <p className="text-sm text-gray-500 truncate">{session.agent_name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={session.status} />
          {hasActiveRuns && (
            <span className="flex h-2 w-2">
              <span className="animate-ping absolute h-2 w-2 rounded-full bg-emerald-400 opacity-75" />
              <span className="relative rounded-full h-2 w-2 bg-emerald-500" />
            </span>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className="space-y-1 mb-3 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Runs:</span>
          <span className={`font-medium ${hasFailed ? 'text-red-600' : 'text-gray-900'}`}>
            {runSummary}
          </span>
        </div>
        {session.childSessionIds.length > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500">Children:</span>
            <span className="font-medium text-gray-900">{session.childSessionIds.length}</span>
          </div>
        )}
        {session.parent_session_id && (
          <div className="flex justify-between">
            <span className="text-gray-500">Parent:</span>
            <span className="font-medium text-gray-900 truncate max-w-[120px]">
              {session.parent_session_id.slice(0, 12)}...
            </span>
          </div>
        )}
      </div>

      {/* Sparkline */}
      <div className="mb-3">
        <ActivitySparkline data={sparklineData} height={32} />
      </div>

      {/* Footer */}
      <div className="text-xs text-gray-500 text-right">
        {session.lastRunAt ? `Last: ${formatRelativeTime(session.lastRunAt)}` : 'No activity'}
      </div>
    </div>
  );
}
```

### 3. ActivitySparkline (`/dashboard/src/components/features/unified-view/cards/ActivitySparkline.tsx`)

```typescript
import { useMemo } from 'react';
import type { SparklineDataPoint } from '@/types/unified';

interface ActivitySparklineProps {
  data: SparklineDataPoint[];
  height?: number;
  width?: number;
}

const statusColors: Record<string, string> = {
  pending: '#9ca3af',
  running: '#10b981',
  completed: '#22c55e',
  failed: '#ef4444',
  stopped: '#6b7280',
};

export function ActivitySparkline({ data, height = 32, width }: ActivitySparklineProps) {
  const { points, viewBox } = useMemo(() => {
    if (data.length === 0) return { points: '', viewBox: '0 0 100 32' };

    const sortedData = [...data].sort((a, b) => a.timestamp - b.timestamp);
    const minTime = sortedData[0].timestamp;
    const maxTime = sortedData[sortedData.length - 1].timestamp;
    const timeRange = maxTime - minTime || 1;

    const maxValue = Math.max(...sortedData.map(d => d.value), 1);

    const pts = sortedData.map((d, i) => {
      const x = ((d.timestamp - minTime) / timeRange) * 100;
      const y = height - (d.value / maxValue) * (height - 4);
      return `${x},${y}`;
    }).join(' ');

    return { points: pts, viewBox: `0 0 100 ${height}` };
  }, [data, height]);

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-xs text-gray-400"
        style={{ height }}
      >
        No activity
      </div>
    );
  }

  return (
    <svg
      viewBox={viewBox}
      className="w-full"
      style={{ height }}
      preserveAspectRatio="none"
    >
      {/* Area fill */}
      <polygon
        points={`0,${height} ${points} 100,${height}`}
        fill="url(#sparklineGradient)"
        opacity={0.3}
      />

      {/* Line */}
      <polyline
        points={points}
        fill="none"
        stroke="#3b82f6"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Data points */}
      {data.map((d, i) => {
        const sortedData = [...data].sort((a, b) => a.timestamp - b.timestamp);
        const minTime = sortedData[0].timestamp;
        const maxTime = sortedData[sortedData.length - 1].timestamp;
        const timeRange = maxTime - minTime || 1;
        const maxValue = Math.max(...sortedData.map(p => p.value), 1);

        const x = ((d.timestamp - minTime) / timeRange) * 100;
        const y = height - (d.value / maxValue) * (height - 4);

        return (
          <circle
            key={d.runId || i}
            cx={x}
            cy={y}
            r="3"
            fill={statusColors[d.status] || '#3b82f6'}
          />
        );
      })}

      <defs>
        <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  );
}
```

### 4. SessionDetailPanel (`/dashboard/src/components/features/unified-view/cards/SessionDetailPanel.tsx`)

```typescript
import { useState } from 'react';
import { X, Clock, Activity, List } from 'lucide-react';
import { StatusBadge } from '@/components/common';
import { RunsSection } from '@/components/features/unified-view/shared/RunsSection';
import { EventTimeline } from '@/components/features/sessions';
import { formatDuration, formatRelativeTime } from '@/utils/time';
import type { SessionWithRuns, SessionRunStats } from '@/types/unified';

interface SessionDetailPanelProps {
  session: SessionWithRuns;
  stats: SessionRunStats | null;
  onClose: () => void;
}

type DetailTab = 'overview' | 'runs' | 'events';

export function SessionDetailPanel({ session, stats, onClose }: SessionDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');

  return (
    <div className="fixed inset-y-0 right-0 w-[480px] bg-white shadow-xl border-l border-gray-200 z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {session.session_id.slice(0, 20)}...
          </h2>
          <div className="flex items-center gap-2 mt-1">
            <StatusBadge status={session.status} />
            {session.agent_name && (
              <span className="text-sm text-gray-500">{session.agent_name}</span>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {[
          { id: 'overview', label: 'Overview', icon: Activity },
          { id: 'runs', label: 'Runs', icon: List },
          { id: 'events', label: 'Events', icon: Clock },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as DetailTab)}
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium
              transition-colors border-b-2 -mb-px
              ${activeTab === id
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
              }
            `}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Session Info */}
            <section>
              <h3 className="text-sm font-medium text-gray-900 mb-3">Session Info</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">ID</dt>
                  <dd className="font-mono text-gray-900">{session.session_id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Created</dt>
                  <dd className="text-gray-900">{formatRelativeTime(session.created_at)}</dd>
                </div>
                {session.parent_session_id && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Parent</dt>
                    <dd className="font-mono text-gray-900 truncate max-w-[200px]">
                      {session.parent_session_id}
                    </dd>
                  </div>
                )}
                {session.childSessionIds.length > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Children</dt>
                    <dd className="text-gray-900">{session.childSessionIds.length} sessions</dd>
                  </div>
                )}
              </dl>
            </section>

            {/* Run Statistics */}
            {stats && (
              <section>
                <h3 className="text-sm font-medium text-gray-900 mb-3">Run Statistics</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900">{stats.totalRuns}</div>
                    <div className="text-xs text-gray-500">Total Runs</div>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">{stats.completedRuns}</div>
                    <div className="text-xs text-gray-500">Completed</div>
                  </div>
                  <div className="p-3 bg-red-50 rounded-lg">
                    <div className="text-2xl font-bold text-red-600">{stats.failedRuns}</div>
                    <div className="text-xs text-gray-500">Failed</div>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {formatDuration(stats.averageDuration)}
                    </div>
                    <div className="text-xs text-gray-500">Avg Duration</div>
                  </div>
                </div>
              </section>
            )}
          </div>
        )}

        {activeTab === 'runs' && (
          <RunsSection runs={session.runs} />
        )}

        {activeTab === 'events' && (
          <EventTimeline sessionId={session.session_id} />
        )}
      </div>
    </div>
  );
}
```

### 5. CardGrid (`/dashboard/src/components/features/unified-view/cards/CardGrid.tsx`)

```typescript
import { SessionCardEnhanced } from './SessionCardEnhanced';
import type { SessionWithRuns, SparklineDataPoint } from '@/types/unified';

interface CardGridProps {
  sessions: SessionWithRuns[];
  loading: boolean;
  onSelectSession: (session: SessionWithRuns) => void;
  selectedSessionId?: string;
  getSparklineData: (sessionId: string) => SparklineDataPoint[];
}

export function CardGrid({
  sessions,
  loading,
  onSelectSession,
  selectedSessionId,
  getSparklineData,
}: CardGridProps) {
  if (loading && sessions.length === 0) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-48 bg-gray-100 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No sessions found
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {sessions.map(session => (
        <SessionCardEnhanced
          key={session.session_id}
          session={session}
          isSelected={selectedSessionId === session.session_id}
          onClick={() => onSelectSession(session)}
          sparklineData={getSparklineData(session.session_id)}
          variant="grid"
        />
      ))}
    </div>
  );
}
```

## File Structure

```
dashboard/src/
├── types/
│   └── unified.ts                 # SessionWithRuns, SessionRunStats, SparklineDataPoint
│
├── hooks/
│   └── useSessionsWithRuns.ts     # Combined session + runs data hook
│
├── utils/
│   └── time.ts                    # formatDuration, formatRelativeTime
│
├── components/
│   └── features/
│       └── unified-view/
│           ├── shared/
│           │   └── RunsSection.tsx
│           │
│           └── cards/
│               ├── index.ts
│               ├── TabHeader.tsx
│               ├── CardGrid.tsx
│               ├── CardList.tsx
│               ├── SessionCardEnhanced.tsx
│               ├── ActivitySparkline.tsx
│               └── SessionDetailPanel.tsx
│
└── pages/
    └── unified-view/
        └── DashboardCardsTab.tsx
```

## Step-by-Step Implementation Order

1. **Create shared types** (`types/unified.ts`)
2. **Create useSessionsWithRuns hook** (`hooks/useSessionsWithRuns.ts`)
3. **Create time utilities** if not existing (`utils/time.ts`)
4. **Create ActivitySparkline** (no dependencies)
5. **Create SessionCardEnhanced** (uses sparkline)
6. **Create CardGrid and CardList** (uses card component)
7. **Create RunsSection** (shared component for panel)
8. **Create SessionDetailPanel** (uses runs section)
9. **Create TabHeader** (filter controls)
10. **Create DashboardCardsTab** (main tab page)

## Key Design Decisions

### Card Layout
- **Grid**: Visual dashboard, best for overview with many sessions
- **List**: Compact, scannable, better for detailed comparison

### Sparkline Design
- Shows run activity over time
- Color-coded points by status (green=completed, red=failed, blue=running)
- Area fill for visual weight

### Detail Panel
- Slide-out from right side (doesn't replace main view)
- Tabbed interface for organized information
- Reuses existing components (EventTimeline, RunsSection)

### Performance
- Memoized filtering and sorting
- Lazy loading of sparkline data
- Skeleton loading states
- Consider virtualization for 100+ sessions