# Approach 3: Hierarchical Tree View

## Status

**Implementation Guide** - Ready for Development

## Overview

This approach displays a **collapsible tree structure** where sessions are parent nodes and runs are child nodes. Child sessions appear as nested subtrees under their parent sessions, providing a bird's-eye view of the entire orchestration hierarchy.

## Architecture Overview

```
▼ orchestrator-main                          finished     2h ago
  │ Status: finished │ Agent: orchestrator │ 4 runs │ 2 children
  │
  ├─ ▶ Run #1 (start_session)               completed    5m 23s
  ├─ ▶ Run #2 (resume_session)              completed    2m 15s
  │
  ├─ ▼ child-1                               finished     1h ago
  │   │ Status: finished │ Agent: researcher │ 1 run
  │   │
  │   └─ ▶ Run #1 (start_session)           completed    3m 10s
  │
  └─ ▼ child-2                               finished     45m ago
      │ Status: finished │ Agent: coder │ 2 runs
      │
      ├─ ▶ Run #1 (start_session)           completed    8m 45s
      └─ ▶ Run #2 (resume_session)          completed    2m 30s
```

## Component Diagram

```
UnifiedViewPage
  │
  ├── TabNavigation (shared)
  │
  └── TreeViewTab
        │
        ├── TreeToolbar
        │     ├── Search
        │     ├── Status Filter
        │     ├── Expand/Collapse All
        │     └── Refresh
        │
        ├── SessionTree
        │     └── SessionTreeNode (recursive)
        │           ├── Session Header
        │           ├── RunTreeNode (repeated)
        │           └── SessionTreeNode (children, recursive)
        │
        └── TreeDetailPanel (slide-out)
              ├── Session Details
              ├── Run Details
              └── Events Timeline
```

## Shared Infrastructure

### 1. Tree Types (`/dashboard/src/types/unified.ts`)

```typescript
import type { Session, Run } from './index';

export interface SessionTreeData {
  session: Session;
  runs: Run[];
  childSessions: SessionTreeData[];
  runCount: number;
  childCount: number;
  latestActivity: string;
  hasActiveRun: boolean;
}

export interface TreeExpandState {
  [nodeId: string]: boolean;
}

export interface UnifiedViewFilters {
  sessionStatus?: Session['status'] | 'all';
  runStatus?: Run['status'] | 'all';
  agentName?: string;
  searchQuery?: string;
}
```

### 2. Tree Builder Utility (`/dashboard/src/utils/treeBuilder.ts`)

```typescript
import type { Session, Run } from '@/types';
import type { SessionTreeData } from '@/types/unified';

export function buildSessionTree(
  sessions: Session[],
  runs: Run[]
): SessionTreeData[] {
  // Index runs by session_id
  const runsBySession = new Map<string, Run[]>();
  runs.forEach(run => {
    const sessionRuns = runsBySession.get(run.session_id) || [];
    sessionRuns.push(run);
    runsBySession.set(run.session_id, sessionRuns);
  });

  // Find root sessions and build tree recursively
  const rootSessions = sessions.filter(s => !s.parent_session_id);

  function buildNode(session: Session): SessionTreeData {
    const sessionRuns = runsBySession.get(session.session_id) || [];
    const childSessions = sessions
      .filter(s => s.parent_session_id === session.session_id)
      .map(buildNode);

    // Sort runs chronologically
    sessionRuns.sort((a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );

    // Determine latest activity
    const timestamps = [
      session.modified_at || session.created_at,
      ...sessionRuns.map(r => r.completed_at || r.started_at || r.created_at),
      ...childSessions.map(c => c.latestActivity),
    ].filter(Boolean) as string[];

    const latestActivity = timestamps.reduce((latest, ts) =>
      new Date(ts) > new Date(latest) ? ts : latest
    );

    const hasActiveRun = sessionRuns.some(r =>
      ['pending', 'claimed', 'running', 'stopping'].includes(r.status)
    );

    return {
      session,
      runs: sessionRuns,
      childSessions,
      runCount: sessionRuns.length,
      childCount: childSessions.length,
      latestActivity,
      hasActiveRun,
    };
  }

  return rootSessions.map(buildNode);
}

export function getTreeStats(tree: SessionTreeData[]) {
  let totalSessions = 0;
  let totalRuns = 0;
  let activeSessions = 0;
  let activeRuns = 0;

  function countNode(node: SessionTreeData) {
    totalSessions++;
    totalRuns += node.runCount;
    if (node.session.status === 'running') activeSessions++;
    if (node.hasActiveRun) {
      activeRuns += node.runs.filter(r =>
        ['running', 'stopping'].includes(r.status)
      ).length;
    }
    node.childSessions.forEach(countNode);
  }

  tree.forEach(countNode);
  return { totalSessions, totalRuns, activeSessions, activeRuns };
}
```

### 3. Tree Hook (`/dashboard/src/hooks/useSessionRunTree.ts`)

```typescript
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSessions } from '@/contexts';
import { runService } from '@/services';
import { buildSessionTree } from '@/utils/treeBuilder';
import type { Run } from '@/types';
import type { SessionTreeData, TreeExpandState } from '@/types/unified';

export function useSessionRunTree(options: { autoRefreshRuns?: boolean } = {}) {
  const { autoRefreshRuns = true } = options;

  const { sessions, loading: sessionsLoading } = useSessions();
  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandState, setExpandState] = useState<TreeExpandState>({});

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
    if (!autoRefreshRuns) return;
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, [autoRefreshRuns, fetchRuns]);

  const tree = useMemo(() => {
    return buildSessionTree(sessions, runs);
  }, [sessions, runs]);

  // Initialize expand state for new sessions
  useEffect(() => {
    setExpandState(prev => {
      const newState = { ...prev };
      sessions.forEach(s => {
        if (!(s.session_id in newState)) {
          newState[s.session_id] = !s.parent_session_id; // Expand roots
        }
      });
      return newState;
    });
  }, [sessions]);

  const expandAll = useCallback(() => {
    const newState: TreeExpandState = {};
    sessions.forEach(s => { newState[s.session_id] = true; });
    setExpandState(newState);
  }, [sessions]);

  const collapseAll = useCallback(() => {
    const newState: TreeExpandState = {};
    sessions.forEach(s => { newState[s.session_id] = false; });
    setExpandState(newState);
  }, [sessions]);

  const toggleNode = useCallback((nodeId: string) => {
    setExpandState(prev => ({ ...prev, [nodeId]: !prev[nodeId] }));
  }, []);

  return {
    tree,
    loading: sessionsLoading,
    runsLoading,
    error,
    expandState,
    expandAll,
    collapseAll,
    toggleNode,
    refreshRuns: fetchRuns,
  };
}
```

## Tab-Specific Components

### 1. TreeViewTab (`/dashboard/src/components/features/unified/TreeViewTab.tsx`)

```typescript
import { useState, useCallback } from 'react';
import { useSessionRunTree } from '@/hooks/useSessionRunTree';
import { TreeToolbar } from './tree/TreeToolbar';
import { SessionTree } from './tree/SessionTree';
import { TreeDetailPanel } from './tree/TreeDetailPanel';
import { LoadingState, EmptyState } from '@/components/common';
import { GitBranch } from 'lucide-react';
import type { Session, Run } from '@/types';
import type { UnifiedViewFilters } from '@/types/unified';

export function TreeViewTab() {
  const {
    tree,
    loading,
    runsLoading,
    error,
    expandState,
    toggleNode,
    expandAll,
    collapseAll,
    refreshRuns,
  } = useSessionRunTree({ autoRefreshRuns: true });

  const [filters, setFilters] = useState<UnifiedViewFilters>({
    sessionStatus: 'all',
    searchQuery: '',
  });

  const [selectedItem, setSelectedItem] = useState<{
    type: 'session' | 'run';
    data: Session | Run;
  } | null>(null);

  if (loading && tree.length === 0) {
    return <LoadingState message="Loading session tree..." />;
  }

  if (tree.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <EmptyState
          icon={<GitBranch className="w-16 h-16" />}
          title="No sessions found"
          description="Sessions will appear here in a hierarchical tree"
        />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <TreeToolbar
        filters={filters}
        onFiltersChange={setFilters}
        onExpandAll={expandAll}
        onCollapseAll={collapseAll}
        onRefresh={refreshRuns}
        isRefreshing={runsLoading}
        tree={tree}
      />

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 overflow-auto bg-gray-50 p-4">
          <SessionTree
            tree={tree}
            expandState={expandState}
            filters={filters}
            onToggleNode={toggleNode}
            onSelectSession={(s) => setSelectedItem({ type: 'session', data: s })}
            onSelectRun={(r) => setSelectedItem({ type: 'run', data: r })}
            selectedItemId={selectedItem?.data && 'session_id' in selectedItem.data
              ? selectedItem.data.session_id
              : selectedItem?.data && 'run_id' in selectedItem.data
              ? selectedItem.data.run_id
              : null}
          />
        </div>

        {selectedItem && (
          <TreeDetailPanel
            type={selectedItem.type}
            data={selectedItem.data}
            onClose={() => setSelectedItem(null)}
          />
        )}
      </div>
    </div>
  );
}
```

### 2. SessionTreeNode (`/dashboard/src/components/features/unified/tree/SessionTreeNode.tsx`)

```typescript
import { ChevronRight, ChevronDown, Bot, Folder, GitBranch } from 'lucide-react';
import { StatusBadge, CopyButton } from '@/components/common';
import { formatRelativeTime } from '@/utils/formatters';
import { RunTreeNode } from './RunTreeNode';
import type { Session, Run } from '@/types';
import type { SessionTreeData, TreeExpandState } from '@/types/unified';

interface SessionTreeNodeProps {
  node: SessionTreeData;
  depth: number;
  isExpanded: boolean;
  expandState: TreeExpandState;
  onToggle: () => void;
  onToggleChild: (nodeId: string) => void;
  onSelectSession: (session: Session) => void;
  onSelectRun: (run: Run) => void;
  selectedItemId: string | null;
}

export function SessionTreeNode({
  node,
  depth,
  isExpanded,
  expandState,
  onToggle,
  onToggleChild,
  onSelectSession,
  onSelectRun,
  selectedItemId,
}: SessionTreeNodeProps) {
  const { session, runs, childSessions, runCount, childCount, hasActiveRun } = node;
  const isSelected = selectedItemId === session.session_id;
  const indentPx = depth * 24;

  const accentColor = session.status === 'running'
    ? 'border-l-emerald-500'
    : session.status === 'stopped'
    ? 'border-l-red-500'
    : 'border-l-gray-300';

  return (
    <div className="relative">
      <div
        className={`relative flex items-start gap-2 p-3 rounded-lg border-l-4 transition-colors cursor-pointer
          ${accentColor}
          ${isSelected ? 'bg-primary-50 ring-2 ring-primary-500' : 'bg-white hover:bg-gray-50 border border-gray-200'}
        `}
        style={{ marginLeft: `${indentPx}px` }}
        onClick={() => onSelectSession(session)}
      >
        <button
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
          className="flex-shrink-0 p-1 hover:bg-gray-100 rounded"
        >
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          hasActiveRun ? 'bg-emerald-100' : 'bg-gray-100'
        }`}>
          <GitBranch className={`w-4 h-4 ${hasActiveRun ? 'text-emerald-600' : 'text-gray-600'}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-gray-900 truncate">{session.session_id.slice(0, 16)}...</span>
            <CopyButton text={session.session_id} />
            <StatusBadge status={session.status} />
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-500">
            {session.agent_name && (
              <span className="flex items-center gap-1">
                <Bot className="w-3 h-3" />
                {session.agent_name}
              </span>
            )}
            <span>{runCount} run{runCount !== 1 ? 's' : ''}</span>
            {childCount > 0 && <span>{childCount} children</span>}
          </div>

          <div className="mt-1 text-xs text-gray-400">
            {formatRelativeTime(session.modified_at || session.created_at)}
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="mt-1 space-y-1">
          {runs.map((run, index) => (
            <RunTreeNode
              key={run.run_id}
              run={run}
              runNumber={index + 1}
              depth={depth + 1}
              isSelected={selectedItemId === run.run_id}
              onSelect={() => onSelectRun(run)}
            />
          ))}

          {childSessions.map(childNode => (
            <SessionTreeNode
              key={childNode.session.session_id}
              node={childNode}
              depth={depth + 1}
              isExpanded={expandState[childNode.session.session_id] ?? false}
              expandState={expandState}
              onToggle={() => onToggleChild(childNode.session.session_id)}
              onToggleChild={onToggleChild}
              onSelectSession={onSelectSession}
              onSelectRun={onSelectRun}
              selectedItemId={selectedItemId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 3. RunTreeNode (`/dashboard/src/components/features/unified/tree/RunTreeNode.tsx`)

```typescript
import { Zap, Play, RotateCw } from 'lucide-react';
import { RunStatusBadge } from '@/components/features/runs/RunStatusBadge';
import { Badge, CopyButton } from '@/components/common';
import { formatRelativeTime } from '@/utils/formatters';
import type { Run } from '@/types';

interface RunTreeNodeProps {
  run: Run;
  runNumber: number;
  depth: number;
  isSelected: boolean;
  onSelect: () => void;
}

export function RunTreeNode({ run, runNumber, depth, isSelected, onSelect }: RunTreeNodeProps) {
  const indentPx = depth * 24;
  const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);
  const TypeIcon = run.type === 'start_session' ? Play : RotateCw;

  const formatDuration = () => {
    if (!run.started_at) return '-';
    const start = new Date(run.started_at);
    const end = run.completed_at ? new Date(run.completed_at) : new Date();
    const diffMs = end.getTime() - start.getTime();
    if (diffMs < 60000) return `${Math.floor(diffMs / 1000)}s`;
    return `${Math.floor(diffMs / 60000)}m ${Math.floor((diffMs % 60000) / 1000)}s`;
  };

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-md transition-colors cursor-pointer ${
        isSelected ? 'bg-primary-50 ring-1 ring-primary-400' : 'bg-white hover:bg-gray-50 border border-gray-100'
      }`}
      style={{ marginLeft: `${indentPx + 12}px` }}
      onClick={onSelect}
    >
      <div className="w-4 h-px bg-gray-300" />

      <div className={`flex-shrink-0 w-6 h-6 rounded flex items-center justify-center ${
        isActive ? 'bg-blue-100' : 'bg-gray-100'
      }`}>
        <Zap className={`w-3 h-3 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
      </div>

      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Run #{runNumber}</span>
        <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
          <TypeIcon className="w-3 h-3 mr-1" />
          {run.type === 'start_session' ? 'start' : 'resume'}
        </Badge>
        <RunStatusBadge status={run.status} />
        <span className="text-xs text-gray-500">{formatDuration()}</span>
      </div>

      <div className="flex items-center gap-1 text-xs text-gray-400 font-mono">
        {run.run_id.slice(0, 8)}
        <CopyButton text={run.run_id} />
      </div>
    </div>
  );
}
```

## File Structure

```
dashboard/src/
├── types/
│   └── unified.ts              # SessionTreeData, TreeExpandState
│
├── utils/
│   └── treeBuilder.ts          # buildSessionTree, getTreeStats
│
├── hooks/
│   └── useSessionRunTree.ts    # Tree data with expand/collapse
│
├── components/
│   └── features/
│       └── unified/
│           ├── index.ts
│           ├── TreeViewTab.tsx
│           └── tree/
│               ├── index.ts
│               ├── TreeToolbar.tsx
│               ├── SessionTree.tsx
│               ├── SessionTreeNode.tsx
│               ├── RunTreeNode.tsx
│               └── TreeDetailPanel.tsx
│
└── pages/
    └── UnifiedView.tsx
```

## Step-by-Step Implementation Order

1. **Create shared types** (`types/unified.ts`)
2. **Create tree builder utility** (`utils/treeBuilder.ts`)
3. **Create tree hook** (`hooks/useSessionRunTree.ts`)
4. **Create RunTreeNode** (leaf node, simplest)
5. **Create SessionTreeNode** (recursive, uses RunTreeNode)
6. **Create SessionTree** (container, applies filters)
7. **Create TreeToolbar** (search, filter, expand/collapse)
8. **Create TreeDetailPanel** (side panel for selection)
9. **Create TreeViewTab** (main component)
10. **Integrate with UnifiedView page**

## Key Design Decisions

### Hierarchical Structure
- Sessions with `parent_session_id` are nested under their parent
- Root sessions (no parent) are top-level nodes
- Runs are always direct children of their session

### Expand/Collapse State
- Root sessions default to expanded
- Child sessions default to collapsed
- State persisted in component (could add localStorage)

### Real-time Updates
- Sessions update via SSE through SessionsContext
- Runs polled every 5 seconds
- Tree rebuilds automatically when data changes
