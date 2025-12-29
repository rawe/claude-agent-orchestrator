# Approach 4: Swimlane Timeline View

## Status

**Implementation Guide** - Ready for Development

## Overview

This approach displays **horizontal swimlanes** where each session is a lane with runs as blocks positioned along a time axis. Similar to a Gantt chart, it clearly shows concurrency, timing relationships, and idle periods between runs.

## Visual Design

```
Timeline                    10:00    10:15    10:30    10:45    11:00
─────────────────────────────────────────────────────────────────────
                              │        │        │        │        │
orchestrator-main     ████████│████    │   ████ │████    │████████│
                       Run #1  │ idle   │ Run #2 │ idle   │ Run #3 │
                              │        │        │        │        │
─────────────────────────────────────────────────────────────────────
                              │        │        │        │        │
child-1 ──────────────────────│████████│████    │        │        │
                              │ Run #1        │ (finished)
                              │        │        │        │        │
─────────────────────────────────────────────────────────────────────

Legend: ████ = run execution   ──── = session idle   ● = running
```

## Component Diagram

```
SwimlaneTab
  │
  ├── TimelineControls
  │     ├── Zoom In/Out
  │     ├── Fit All
  │     ├── Jump to Now
  │     └── Refresh
  │
  ├── TimelineHeader (time axis)
  │     └── Time Markers
  │
  ├── SwimlaneContainer (scrollable)
  │     └── Swimlane (per session)
  │           ├── Session Label
  │           └── RunBlock (positioned by time)
  │                 └── RunTooltip (on hover)
  │
  └── RunDetailPanel (on selection)
```

## Shared Infrastructure

### 1. Timeline Types (`/dashboard/src/types/unified-view.ts`)

```typescript
export interface TimelineViewport {
  startTime: Date;
  endTime: Date;
  pixelsPerMs: number;
}

export interface TimelineConfig {
  minZoom: number;      // Min ms per pixel
  maxZoom: number;      // Max ms per pixel
  defaultZoom: number;
  swimlaneHeight: number;
  runBlockMinWidth: number;
  timeAxisHeight: number;
}

export const DEFAULT_TIMELINE_CONFIG: TimelineConfig = {
  minZoom: 100,         // 100ms per pixel (zoomed in)
  maxZoom: 3600000,     // 1 hour per pixel (zoomed out)
  defaultZoom: 60000,   // 1 minute per pixel
  swimlaneHeight: 48,
  runBlockMinWidth: 8,
  timeAxisHeight: 40,
};
```

### 2. Timeline Utilities (`/dashboard/src/utils/timeline.ts`)

```typescript
import type { TimelineViewport, TimelineConfig } from '@/types/unified-view';

export function timeToPixel(time: Date, viewport: TimelineViewport): number {
  const ms = time.getTime() - viewport.startTime.getTime();
  return ms * viewport.pixelsPerMs;
}

export function pixelToTime(pixel: number, viewport: TimelineViewport): Date {
  const ms = pixel / viewport.pixelsPerMs;
  return new Date(viewport.startTime.getTime() + ms);
}

export function calculateRunBlockPosition(
  run: { created_at: string; started_at: string | null; completed_at: string | null; status: string },
  viewport: TimelineViewport,
  config: TimelineConfig
): { left: number; width: number } {
  const startTime = new Date(run.started_at || run.created_at);
  const endTime = run.completed_at
    ? new Date(run.completed_at)
    : ['pending', 'claimed', 'running', 'stopping'].includes(run.status)
      ? new Date()
      : startTime;

  const left = timeToPixel(startTime, viewport);
  const durationMs = endTime.getTime() - startTime.getTime();
  const width = Math.max(durationMs * viewport.pixelsPerMs, config.runBlockMinWidth);

  return { left, width };
}

export function generateTimeMarkers(
  viewport: TimelineViewport,
  containerWidth: number
): { time: Date; label: string; position: number }[] {
  const markers: { time: Date; label: string; position: number }[] = [];
  const viewportDurationMs = viewport.endTime.getTime() - viewport.startTime.getTime();

  // Determine interval based on zoom
  let intervalMs: number;
  if (viewportDurationMs <= 60000) intervalMs = 5000;        // 5s for < 1min
  else if (viewportDurationMs <= 600000) intervalMs = 60000; // 1min for < 10min
  else if (viewportDurationMs <= 3600000) intervalMs = 300000; // 5min for < 1hr
  else intervalMs = 1800000; // 30min for > 1hr

  const startMs = Math.floor(viewport.startTime.getTime() / intervalMs) * intervalMs;

  for (let ms = startMs; ms <= viewport.endTime.getTime(); ms += intervalMs) {
    const time = new Date(ms);
    if (time >= viewport.startTime) {
      markers.push({
        time,
        label: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        position: timeToPixel(time, viewport),
      });
    }
  }

  return markers;
}

export function calculateFitAllViewport(
  timeRanges: { start: Date | null; end: Date | null }[],
  containerWidth: number,
  padding: number = 50
): TimelineViewport | null {
  let globalStart: Date | null = null;
  let globalEnd: Date | null = null;

  timeRanges.forEach(({ start, end }) => {
    if (start && (!globalStart || start < globalStart)) globalStart = start;
    if (end && (!globalEnd || end > globalEnd)) globalEnd = end;
  });

  if (!globalStart || !globalEnd) return null;

  const durationMs = globalEnd.getTime() - globalStart.getTime();
  const availableWidth = containerWidth - 2 * padding;
  const pixelsPerMs = availableWidth / durationMs;
  const paddingMs = padding / pixelsPerMs;

  return {
    startTime: new Date(globalStart.getTime() - paddingMs),
    endTime: new Date(globalEnd.getTime() + paddingMs),
    pixelsPerMs,
  };
}
```

## Tab-Specific Components

### 1. SwimlaneTab (`/dashboard/src/pages/unified-view/SwimlaneTab.tsx`)

```typescript
import { useState, useRef, useCallback, useEffect } from 'react';
import { useSessionsWithRuns } from '@/hooks/useSessionsWithRuns';
import { TimelineHeader } from '@/components/features/unified-view/swimlane/TimelineHeader';
import { SwimlaneContainer } from '@/components/features/unified-view/swimlane/SwimlaneContainer';
import { TimelineControls } from '@/components/features/unified-view/swimlane/TimelineControls';
import { calculateFitAllViewport, DEFAULT_TIMELINE_CONFIG } from '@/utils/timeline';
import type { TimelineViewport } from '@/types/unified-view';
import type { Run } from '@/types';

export function SwimlaneTab() {
  const { sessionsWithRuns, globalTimeRange, loading, refreshRuns } = useSessionsWithRuns();
  const containerRef = useRef<HTMLDivElement>(null);

  const [viewport, setViewport] = useState<TimelineViewport | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [hoveredRun, setHoveredRun] = useState<Run | null>(null);

  // Observe container width
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      setContainerWidth(entries[0]?.contentRect.width || 0);
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Initialize viewport
  useEffect(() => {
    if (!containerWidth || !globalTimeRange.start || !globalTimeRange.end) return;
    if (!viewport) {
      const initial = calculateFitAllViewport([globalTimeRange], containerWidth - 200, 50);
      if (initial) setViewport(initial);
    }
  }, [containerWidth, globalTimeRange, viewport]);

  const handleZoom = useCallback((direction: 'in' | 'out', centerX?: number) => {
    if (!viewport) return;
    const factor = direction === 'in' ? 1.5 : 0.67;
    const newPixelsPerMs = Math.max(
      1 / DEFAULT_TIMELINE_CONFIG.maxZoom,
      Math.min(1 / DEFAULT_TIMELINE_CONFIG.minZoom, viewport.pixelsPerMs * factor)
    );

    const viewportDuration = viewport.endTime.getTime() - viewport.startTime.getTime();
    const newDuration = viewportDuration / factor;
    const centerTime = centerX !== undefined
      ? new Date(viewport.startTime.getTime() + centerX / viewport.pixelsPerMs)
      : new Date((viewport.startTime.getTime() + viewport.endTime.getTime()) / 2);

    setViewport({
      startTime: new Date(centerTime.getTime() - newDuration / 2),
      endTime: new Date(centerTime.getTime() + newDuration / 2),
      pixelsPerMs: newPixelsPerMs,
    });
  }, [viewport]);

  const handlePan = useCallback((deltaX: number) => {
    if (!viewport) return;
    const deltaMs = deltaX / viewport.pixelsPerMs;
    setViewport({
      ...viewport,
      startTime: new Date(viewport.startTime.getTime() - deltaMs),
      endTime: new Date(viewport.endTime.getTime() - deltaMs),
    });
  }, [viewport]);

  const handleFitAll = useCallback(() => {
    if (!containerWidth || !globalTimeRange.start) return;
    const newViewport = calculateFitAllViewport([globalTimeRange], containerWidth - 200, 50);
    if (newViewport) setViewport(newViewport);
  }, [containerWidth, globalTimeRange]);

  return (
    <div className="h-full flex flex-col overflow-hidden" ref={containerRef}>
      <TimelineControls
        onZoomIn={() => handleZoom('in')}
        onZoomOut={() => handleZoom('out')}
        onFitAll={handleFitAll}
        onJumpToNow={() => {/* jump to now */}}
        onRefresh={refreshRuns}
      />

      {viewport && (
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <TimelineHeader viewport={viewport} sessionLabelWidth={200} />
          <SwimlaneContainer
            sessionsWithRuns={sessionsWithRuns}
            viewport={viewport}
            sessionLabelWidth={200}
            onPan={handlePan}
            onZoom={handleZoom}
            selectedRun={selectedRun}
            hoveredRun={hoveredRun}
            onSelectRun={setSelectedRun}
            onHoverRun={setHoveredRun}
          />
        </div>
      )}
    </div>
  );
}
```

### 2. RunBlock Component

```typescript
import { useMemo } from 'react';
import { calculateRunBlockPosition, DEFAULT_TIMELINE_CONFIG } from '@/utils/timeline';
import type { TimelineViewport } from '@/types/unified-view';
import type { Run, RunStatus } from '@/types';

interface RunBlockProps {
  run: Run;
  runNumber: number;
  viewport: TimelineViewport;
  isSelected: boolean;
  isHovered: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

const statusColors: Record<RunStatus, string> = {
  pending: 'bg-gray-300',
  claimed: 'bg-blue-300',
  running: 'bg-emerald-400',
  stopping: 'bg-amber-400',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  stopped: 'bg-gray-500',
};

export function RunBlock({
  run,
  runNumber,
  viewport,
  isSelected,
  isHovered,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: RunBlockProps) {
  const { left, width } = useMemo(
    () => calculateRunBlockPosition(run, viewport, DEFAULT_TIMELINE_CONFIG),
    [run, viewport]
  );

  const isRunning = run.status === 'running';

  return (
    <div
      className={`absolute top-1/2 -translate-y-1/2 h-6 rounded-md border-2 cursor-pointer
        transition-all duration-150 ${statusColors[run.status]}
        ${isSelected ? 'ring-2 ring-primary-500 ring-offset-1 z-20' : 'z-10'}
        ${isHovered ? 'scale-105 shadow-lg z-20' : ''}
        ${isRunning ? 'animate-pulse' : ''}
      `}
      style={{ left: `${left}px`, width: `${width}px`, minWidth: 8 }}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {width > 30 && (
        <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white">
          #{runNumber}
        </span>
      )}
    </div>
  );
}
```

### 3. Swimlane Component

```typescript
import { RunBlock } from './RunBlock';
import { StatusBadge } from '@/components/common';
import { DEFAULT_TIMELINE_CONFIG } from '@/types/unified-view';
import type { SessionWithRuns, TimelineViewport } from '@/types/unified-view';
import type { Run } from '@/types';

interface SwimlaneProps {
  sessionWithRuns: SessionWithRuns;
  viewport: TimelineViewport;
  sessionLabelWidth: number;
  timelineWidth: number;
  selectedRun: Run | null;
  hoveredRun: Run | null;
  onSelectRun: (run: Run | null) => void;
  onHoverRun: (run: Run | null) => void;
}

export function Swimlane({
  sessionWithRuns,
  viewport,
  sessionLabelWidth,
  timelineWidth,
  selectedRun,
  hoveredRun,
  onSelectRun,
  onHoverRun,
}: SwimlaneProps) {
  const { session, runs } = sessionWithRuns;

  return (
    <div
      className="flex border-b border-gray-100 hover:bg-gray-50/50"
      style={{ height: DEFAULT_TIMELINE_CONFIG.swimlaneHeight }}
    >
      {/* Session label */}
      <div
        className="flex-shrink-0 flex items-center gap-2 px-3 border-r border-gray-200 bg-white"
        style={{ width: sessionLabelWidth }}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 truncate">
              {session.session_id.slice(0, 12)}...
            </span>
            <StatusBadge status={session.status} />
          </div>
          {session.agent_name && (
            <span className="text-xs text-gray-500 truncate block">
              {session.agent_name}
            </span>
          )}
        </div>
      </div>

      {/* Timeline track */}
      <div className="relative flex-1" style={{ width: timelineWidth }}>
        <div className="absolute inset-y-0 left-0 right-0 flex items-center">
          <div className="h-1 w-full bg-gray-100 rounded" />
        </div>

        {runs.map((run, index) => (
          <RunBlock
            key={run.run_id}
            run={run}
            runNumber={index + 1}
            viewport={viewport}
            isSelected={selectedRun?.run_id === run.run_id}
            isHovered={hoveredRun?.run_id === run.run_id}
            onClick={() => onSelectRun(run)}
            onMouseEnter={() => onHoverRun(run)}
            onMouseLeave={() => onHoverRun(null)}
          />
        ))}
      </div>
    </div>
  );
}
```

## File Structure

```
dashboard/src/
├── types/
│   └── unified-view.ts         # TimelineViewport, TimelineConfig
│
├── utils/
│   └── timeline.ts             # Time-to-pixel utilities
│
├── hooks/
│   └── useSessionsWithRuns.ts  # Combined data hook
│
├── components/
│   └── features/
│       └── unified-view/
│           └── swimlane/
│               ├── index.ts
│               ├── TimelineControls.tsx
│               ├── TimelineHeader.tsx
│               ├── SwimlaneContainer.tsx
│               ├── Swimlane.tsx
│               ├── RunBlock.tsx
│               └── RunTooltip.tsx
│
└── pages/
    └── unified-view/
        └── SwimlaneTab.tsx
```

## Step-by-Step Implementation Order

1. **Create timeline types** (`types/unified-view.ts`)
2. **Create timeline utilities** (`utils/timeline.ts`)
3. **Create RunTooltip** (simplest component)
4. **Create RunBlock** (uses tooltip, positioning)
5. **Create Swimlane** (uses RunBlock)
6. **Create SwimlaneContainer** (handles pan/zoom)
7. **Create TimelineHeader** (time axis)
8. **Create TimelineControls** (zoom/pan buttons)
9. **Create SwimlaneTab** (main page)

## Key Design Decisions

### Zoom/Pan UX
- **Ctrl+Wheel**: Zoom around cursor
- **Shift+Wheel**: Horizontal pan
- **Click+Drag**: Pan timeline
- **Fit All**: Calculate viewport for all runs
- **Now**: Jump to current time

### Performance
- Only render visible time range
- Debounce pan/zoom updates
- Memoize run block positions
- Consider virtualization for 50+ sessions
