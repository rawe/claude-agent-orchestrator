# Mock Implementation Guide for Unified View Approaches

## Overview

This guide documents the pattern used to implement mock visualizations for comparing different session/run view approaches in the dashboard. Each approach is implemented as a **tab** within a single `UnifiedView` page, allowing side-by-side comparison without backend integration.

## File Structure

```
dashboard/src/pages/
├── UnifiedView.tsx              # Main page with tab navigation only (~95 lines)
└── unified-view/
    ├── index.ts                 # Barrel exports (re-exports all modules)
    ├── types.ts                 # MockSession, MockRun, ActivityType, etc.
    ├── utils.ts                 # formatRelativeTime, formatDuration, getEventTypeStyles
    ├── mock-data.ts             # mockSessions, mockRuns arrays
    ├── SessionTimelineTab.tsx   # Approach 1
    ├── RunCentricTab.tsx        # Approach 2
    ├── TreeViewTab.tsx          # Approach 3
    ├── SwimlaneTab.tsx          # Approach 4
    └── ActivityFeedTab.tsx      # Approach 5
```

The page is:
- Routed at `/unified` (configured in `dashboard/src/router.tsx`)
- Accessible via "Unified View" in the sidebar (configured in `dashboard/src/components/layout/Sidebar.tsx`)

## Architecture Pattern

### 1. Single Page with Tab Navigation

The `UnifiedView` page uses internal tab navigation to switch between approaches:

```typescript
type TabId = 'session-timeline' | 'run-centric' | 'tree-view'; // Add new tab IDs here

function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  const tabs = [
    { id: 'session-timeline' as TabId, label: 'Session Timeline', icon: Layers, description: '...' },
    { id: 'run-centric' as TabId, label: 'Run Centric', icon: Zap, description: '...' },
    { id: 'tree-view' as TabId, label: 'Tree View', icon: GitBranch, description: '...' },
    // Add new tabs here
  ];
  // ... render tab buttons
}

export function UnifiedView() {
  const [activeTab, setActiveTab] = useState<TabId>('session-timeline');

  return (
    <div className="h-full flex flex-col">
      {/* Header with TabNavigation */}
      <div className="...">
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
      </div>

      {/* Tab Content - each approach is a separate component */}
      {activeTab === 'session-timeline' && <SessionTimelineTab />}
      {activeTab === 'run-centric' && <RunCentricTab />}
      {activeTab === 'tree-view' && <TreeViewTab />}
      {/* Add new tab components here */}
    </div>
  );
}
```

### 2. Imports in Tab Components

Each tab component imports shared dependencies from the barrel export:

```typescript
import { useState } from 'react';
import { Badge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import { SomeIcon, AnotherIcon } from 'lucide-react';
import {
  MockSession,
  MockRun,
  TabId,
  mockSessions,
  mockRuns,
  formatRelativeTime,
  formatDuration,
  getEventTypeStyles,
} from './';  // Import from barrel (index.ts)
```

### 3. Mock Data Structure

Mock data is defined in `mock-data.ts`. The data models mirror the real API types but with simplified fields:

```typescript
// Sessions with parent-child relationships for hierarchical views
const mockSessions = [
  {
    session_id: 'session-orchestrator-main',
    name: 'orchestrator-main',
    agent_name: 'orchestrator',
    status: 'finished' as const,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    project_dir: '/projects/data-pipeline',
    parent_session_id: null as string | null,  // Root session
    runCount: 3,
    latestRunStatus: 'completed' as const,
  },
  {
    session_id: 'session-child-researcher',
    name: 'child-researcher',
    agent_name: 'researcher',
    status: 'finished' as const,
    created_at: new Date(Date.now() - 1.8 * 60 * 60 * 1000).toISOString(),
    parent_session_id: 'session-orchestrator-main',  // Child of orchestrator
    // ...
  },
  // More sessions...
];

// Runs with events for timeline visualization
const mockRuns = [
  {
    run_id: 'run-001',
    session_id: 'session-orchestrator-main',  // Links to session
    type: 'start_session' as const,
    status: 'completed' as const,
    prompt: 'Task description...',
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    started_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 5000).toISOString(),
    completed_at: new Date(Date.now() - 2 * 60 * 60 * 1000 + 323000).toISOString(),
    runner_id: 'runner-abc123def',
    agent_name: 'orchestrator',
    runNumber: 1,
    events: [
      { type: 'session_start', timestamp: '10:00:00', summary: 'Session initialized' },
      { type: 'tool_call', timestamp: '10:00:45', summary: 'start_agent_session (child-1)' },
      { type: 'assistant', timestamp: '10:01:02', summary: 'Started 2 child agents...' },
      // More events...
    ],
  },
  // More runs...
];
```

**Key mock data relationships:**
- Sessions link via `parent_session_id` for hierarchy
- Runs link to sessions via `session_id`
- Events are embedded arrays within runs
- Use relative timestamps: `new Date(Date.now() - X * 60 * 1000).toISOString()`

### 4. TypeScript Interfaces

Types are defined in `types.ts`:

```typescript
interface MockSession {
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

interface MockRun {
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
}
```

### 5. Utility Functions

Shared utilities are in `utils.ts`:

```typescript
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${remainingSeconds}s`;
}

function getEventTypeStyles(type: string) {
  switch (type) {
    case 'session_start':
    case 'session_resume':
      return 'bg-blue-100 text-blue-700 border-blue-200';
    case 'tool_call':
      return 'bg-purple-100 text-purple-700 border-purple-200';
    // ... more event type styles
  }
}
```

### 6. Reusing Existing Components

Import and use existing dashboard components:

```typescript
import { Badge, StatusBadge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
```

These provide consistent styling for status indicators.

### 7. Icons from Lucide

```typescript
import {
  Layers,        // Session Timeline tab
  Zap,           // Run Centric tab / runs
  GitBranch,     // Tree View tab
  ChevronDown,   // Expand
  ChevronRight,  // Collapse
  Play,          // start_session run type
  RotateCcw,     // resume_session run type
  Clock,         // Duration
  Bot,           // Agent
  Search,        // Search input
  Filter,        // Filter dropdown
  X,             // Close panel
  // Add more as needed
} from 'lucide-react';
```

## How to Add a New Approach

### Step 1: Update Types

In `unified-view/types.ts`, add the new tab ID:
```typescript
export type TabId = 'session-timeline' | 'run-centric' | 'tree-view' | 'swimlane' | 'activity-feed' | 'your-new-tab';
```

### Step 2: Create Tab Component File

Create `unified-view/YourNewTab.tsx`:

```typescript
import { useState } from 'react';
import { Badge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import { YourIcon } from 'lucide-react';
import {
  MockSession,
  MockRun,
  mockSessions,
  mockRuns,
  formatRelativeTime,
  formatDuration,
  getEventTypeStyles,
} from './';

export function YourNewTab() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="flex-1 flex min-h-0">
      {/* Left panel: list/tree/timeline */}
      <div className="w-80 border-r border-gray-200 bg-white flex-shrink-0 flex flex-col">
        {/* Your list rendering */}
      </div>

      {/* Right panel: detail view */}
      <div className="flex-1 bg-gray-50 flex flex-col">
        {/* Your detail rendering */}
      </div>
    </div>
  );
}
```

### Step 3: Update Barrel Export

In `unified-view/index.ts`, add:
```typescript
export * from './YourNewTab';
```

### Step 4: Update UnifiedView.tsx

1. Add import (already available via barrel):
```typescript
import { TabId, SessionTimelineTab, ..., YourNewTab } from './unified-view';
```

2. Add tab definition in `TabNavigation`:
```typescript
{ id: 'your-new-tab' as TabId, label: 'Your Tab Name', icon: YourIcon, description: 'Brief description' },
```

3. Add conditional render:
```typescript
{activeTab === 'your-new-tab' && <YourNewTab />}
```

### Step 5: Add Mock Data/Types (if needed)

If your approach needs additional types, add to `types.ts`.
If it needs additional mock data fields, extend `mock-data.ts`.

## Common UI Patterns Used

### Master-Detail Layout
```
┌─────────────────────────────────────────────────┐
│ Header with Tab Navigation                       │
├──────────────┬──────────────────────────────────┤
│ List/Tree    │ Detail Panel                     │
│ (selectable) │ (shows selected item details)    │
│              │                                  │
└──────────────┴──────────────────────────────────┘
```

### Collapsible Sections
Use `useState` for expand state, `ChevronDown`/`ChevronRight` icons.

### Status Indicators
- Use `StatusBadge` for session status (running/finished/stopped)
- Use `RunStatusBadge` for run status (pending/running/completed/failed)
- Use colored left borders for visual status (emerald=active, gray=finished, red=stopped)

### Selection Highlighting
```typescript
className={`... ${isSelected ? 'bg-primary-50 ring-2 ring-primary-500' : 'bg-white hover:bg-gray-50'}`}
```

## Build & Test

After making changes:
```bash
cd dashboard
npm run build  # Verify no TypeScript errors
npm run dev    # Start dev server (use VITE_AUTH0_AUDIENCE= to disable auth)
```

Access at: `http://localhost:3000/unified`

## File Structure Summary

```
dashboard/src/
├── pages/
│   ├── UnifiedView.tsx      # Main page (~95 lines) - tab navigation only
│   ├── index.ts             # Export UnifiedView
│   └── unified-view/
│       ├── index.ts         # Barrel exports
│       ├── types.ts         # Type definitions
│       ├── utils.ts         # Utility functions
│       ├── mock-data.ts     # Mock data arrays
│       └── *Tab.tsx         # Each approach in its own file
├── router.tsx               # Route: /unified -> UnifiedView
└── components/
    └── layout/
        └── Sidebar.tsx      # Nav link to /unified
```

## Tips

1. **Keep it visual**: Focus on layout and interaction patterns, not real data fetching
2. **Mock realistic scenarios**: Include parent-child sessions, multiple runs, various statuses
3. **Use relative times**: `Date.now() - X * 60 * 1000` for realistic "2h ago" displays
4. **Reuse components**: Import existing Badge, StatusBadge components for consistency
5. **Export the main component**: Each tab file should export its main component (e.g., `export function YourNewTab()`)
6. **Badge for mock indicator**: Add `<Badge variant="warning" size="sm">Mock</Badge>` in header
