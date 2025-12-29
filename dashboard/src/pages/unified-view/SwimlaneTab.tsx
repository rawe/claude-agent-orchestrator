import { useState } from 'react';
import {
  Clock,
  X,
  ZoomIn,
  ZoomOut,
  Maximize2,
  SkipForward,
  RefreshCw,
} from 'lucide-react';
import { Badge, StatusBadge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import { MockSession, MockRun } from './types';
import { mockSessions, mockRuns } from './mock-data';
import { formatRelativeTime, formatDuration, getEventTypeStyles } from './utils';

// ============================================================================
// APPROACH 4: SWIMLANE TIMELINE TAB
// ============================================================================

interface TimelineViewport {
  startTime: Date;
  endTime: Date;
  pixelsPerMs: number;
}

interface TimelineConfig {
  minZoom: number;
  maxZoom: number;
  defaultZoom: number;
  swimlaneHeight: number;
  runBlockMinWidth: number;
  timeAxisHeight: number;
  sessionLabelWidth: number;
}

const DEFAULT_TIMELINE_CONFIG: TimelineConfig = {
  minZoom: 100,
  maxZoom: 3600000,
  defaultZoom: 60000,
  swimlaneHeight: 48,
  runBlockMinWidth: 8,
  timeAxisHeight: 40,
  sessionLabelWidth: 200,
};

function timeToPixel(time: Date, viewport: TimelineViewport): number {
  const ms = time.getTime() - viewport.startTime.getTime();
  return ms * viewport.pixelsPerMs;
}

function calculateRunBlockPosition(
  run: MockRun,
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

function generateTimeMarkers(
  viewport: TimelineViewport,
): { time: Date; label: string; position: number }[] {
  const markers: { time: Date; label: string; position: number }[] = [];
  const viewportDurationMs = viewport.endTime.getTime() - viewport.startTime.getTime();

  let intervalMs: number;
  if (viewportDurationMs <= 60000) intervalMs = 5000;
  else if (viewportDurationMs <= 600000) intervalMs = 60000;
  else if (viewportDurationMs <= 3600000) intervalMs = 300000;
  else intervalMs = 1800000;

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

function calculateFitAllViewport(
  runs: MockRun[],
  containerWidth: number,
  padding: number = 50
): TimelineViewport | null {
  if (runs.length === 0) return null;

  const timeRanges = runs.map((run) => {
    const start = new Date(run.started_at || run.created_at);
    const end = run.completed_at
      ? new Date(run.completed_at)
      : ['pending', 'claimed', 'running', 'stopping'].includes(run.status)
        ? new Date()
        : start;
    return { start, end };
  });

  const startTimes = timeRanges.map((r) => r.start.getTime());
  const endTimes = timeRanges.map((r) => r.end.getTime());

  const globalStartMs = Math.min(...startTimes);
  const globalEndMs = Math.max(...endTimes);

  const durationMs = globalEndMs - globalStartMs || 60000;
  const availableWidth = containerWidth - 2 * padding;
  const pixelsPerMs = Math.max(availableWidth / durationMs, 0.00001);
  const paddingMs = padding / pixelsPerMs;

  return {
    startTime: new Date(globalStartMs - paddingMs),
    endTime: new Date(globalEndMs + paddingMs),
    pixelsPerMs,
  };
}

interface TimelineControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitAll: () => void;
  onJumpToNow: () => void;
  onRefresh: () => void;
}

function TimelineControls({ onZoomIn, onZoomOut, onFitAll, onJumpToNow, onRefresh }: TimelineControlsProps) {
  return (
    <div className="flex items-center gap-1 px-4 py-2 bg-white border-b border-gray-200">
      <button
        onClick={onZoomIn}
        className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
        title="Zoom In"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      <button
        onClick={onZoomOut}
        className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
        title="Zoom Out"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
      <div className="w-px h-5 bg-gray-200 mx-1" />
      <button
        onClick={onFitAll}
        className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
        title="Fit All"
      >
        <Maximize2 className="w-4 h-4" />
        <span>Fit All</span>
      </button>
      <button
        onClick={onJumpToNow}
        className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
        title="Jump to Now"
      >
        <SkipForward className="w-4 h-4" />
        <span>Now</span>
      </button>
      <div className="w-px h-5 bg-gray-200 mx-1" />
      <button
        onClick={onRefresh}
        className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
        title="Refresh"
      >
        <RefreshCw className="w-4 h-4" />
      </button>
    </div>
  );
}

interface TimelineHeaderProps {
  viewport: TimelineViewport;
  config: TimelineConfig;
  timelineWidth: number;
}

function TimelineHeader({ viewport, config, timelineWidth }: TimelineHeaderProps) {
  const markers = generateTimeMarkers(viewport);

  return (
    <div className="flex border-b border-gray-200 bg-gray-50" style={{ height: config.timeAxisHeight }}>
      <div
        className="flex-shrink-0 flex items-center px-3 border-r border-gray-200 bg-white"
        style={{ width: config.sessionLabelWidth }}
      >
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Sessions</span>
      </div>
      <div className="relative flex-1 overflow-hidden" style={{ width: timelineWidth }}>
        {markers.map((marker, index) => (
          <div
            key={index}
            className="absolute top-0 bottom-0 flex flex-col items-center justify-end pb-1"
            style={{ left: marker.position }}
          >
            <div className="h-3 w-px bg-gray-300" />
            <span className="text-xs text-gray-500 font-mono whitespace-nowrap">{marker.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface SwimlaneRunBlockProps {
  run: MockRun;
  runNumber: number;
  viewport: TimelineViewport;
  config: TimelineConfig;
  isSelected: boolean;
  isHovered: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

const runStatusColors: Record<string, string> = {
  pending: 'bg-gray-300 border-gray-400',
  claimed: 'bg-blue-300 border-blue-400',
  running: 'bg-emerald-400 border-emerald-500',
  stopping: 'bg-amber-400 border-amber-500',
  completed: 'bg-green-500 border-green-600',
  failed: 'bg-red-500 border-red-600',
  stopped: 'bg-gray-500 border-gray-600',
};

function SwimlaneRunBlock({
  run,
  runNumber,
  viewport,
  config,
  isSelected,
  isHovered,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: SwimlaneRunBlockProps) {
  const { left, width } = calculateRunBlockPosition(run, viewport, config);
  const isRunning = run.status === 'running';

  return (
    <div
      className={`absolute top-1/2 -translate-y-1/2 h-6 rounded-md border-2 cursor-pointer
        transition-all duration-150 ${runStatusColors[run.status] || runStatusColors.pending}
        ${isSelected ? 'ring-2 ring-primary-500 ring-offset-1 z-20' : 'z-10'}
        ${isHovered ? 'scale-105 shadow-lg z-20' : ''}
        ${isRunning ? 'animate-pulse' : ''}
      `}
      style={{ left: `${left}px`, width: `${width}px`, minWidth: 8 }}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      title={`Run #${runNumber} (${run.type}) - ${run.status}`}
    >
      {width > 30 && (
        <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white drop-shadow">
          #{runNumber}
        </span>
      )}
    </div>
  );
}

interface SwimlaneProps {
  session: MockSession;
  runs: MockRun[];
  viewport: TimelineViewport;
  config: TimelineConfig;
  timelineWidth: number;
  selectedRunId: string | null;
  hoveredRunId: string | null;
  onSelectRun: (runId: string | null) => void;
  onHoverRun: (runId: string | null) => void;
}

function Swimlane({
  session,
  runs,
  viewport,
  config,
  timelineWidth,
  selectedRunId,
  hoveredRunId,
  onSelectRun,
  onHoverRun,
}: SwimlaneProps) {
  const isActive = session.status === 'running';

  return (
    <div
      className={`flex border-b border-gray-100 ${isActive ? 'bg-emerald-50/30' : 'hover:bg-gray-50/50'}`}
      style={{ height: config.swimlaneHeight }}
    >
      <div
        className={`flex-shrink-0 flex items-center gap-2 px-3 border-r border-gray-200 bg-white ${
          isActive ? 'border-l-2 border-l-emerald-500' : ''
        }`}
        style={{ width: config.sessionLabelWidth }}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 truncate">{session.name}</span>
            <StatusBadge status={session.status} />
          </div>
          {session.agent_name && (
            <span className="text-xs text-gray-500 truncate block">{session.agent_name}</span>
          )}
        </div>
      </div>

      <div className="relative flex-1" style={{ width: timelineWidth }}>
        <div className="absolute inset-y-0 left-0 right-0 flex items-center">
          <div className="h-1 w-full bg-gray-100 rounded" />
        </div>

        {runs.map((run, index) => (
          <SwimlaneRunBlock
            key={run.run_id}
            run={run}
            runNumber={index + 1}
            viewport={viewport}
            config={config}
            isSelected={selectedRunId === run.run_id}
            isHovered={hoveredRunId === run.run_id}
            onClick={() => onSelectRun(run.run_id)}
            onMouseEnter={() => onHoverRun(run.run_id)}
            onMouseLeave={() => onHoverRun(null)}
          />
        ))}
      </div>
    </div>
  );
}

interface RunDetailPanelProps {
  run: MockRun;
  onClose: () => void;
}

function RunDetailPanel({ run, onClose }: RunDetailPanelProps) {
  const getDuration = () => {
    if (!run.started_at) return '-';
    const start = new Date(run.started_at).getTime();
    const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now();
    return formatDuration(end - start);
  };

  return (
    <div className="w-80 border-l border-gray-200 bg-white flex flex-col flex-shrink-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">Run #{run.runNumber}</h3>
          <RunStatusBadge status={run.status} />
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
              {run.type === 'start_session' ? 'start' : 'resume'}
            </Badge>
            <span className="text-sm text-gray-600">{run.agent_name}</span>
          </div>
          <div className="text-xs text-gray-500 font-mono mb-3">{run.run_id}</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-1 text-gray-500">
              <Clock className="w-3 h-3" />
              {getDuration()}
            </div>
            <div className="text-gray-500">{formatRelativeTime(run.created_at)}</div>
          </div>
        </div>

        <div>
          <h5 className="text-sm font-medium text-gray-700 mb-2">Prompt</h5>
          <div className="p-2 bg-gray-50 rounded text-sm text-gray-700 max-h-24 overflow-y-auto">
            {run.prompt}
          </div>
        </div>

        <div>
          <h5 className="text-sm font-medium text-gray-700 mb-2">Events ({run.events.length})</h5>
          <div className="space-y-2 pl-3 border-l-2 border-gray-200 max-h-64 overflow-y-auto">
            {run.events.map((event, index) => (
              <div key={index} className="py-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${getEventTypeStyles(event.type)}`}>
                    {event.type}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">{event.timestamp}</span>
                </div>
                <p className="text-sm text-gray-600">{event.summary}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function SwimlaneTab() {
  const [viewport, setViewport] = useState<TimelineViewport | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [hoveredRunId, setHoveredRunId] = useState<string | null>(null);

  const config = DEFAULT_TIMELINE_CONFIG;
  const containerWidth = 1000;
  const timelineWidth = containerWidth - config.sessionLabelWidth;

  const sessionsWithRuns = mockSessions.map((session) => ({
    session,
    runs: mockRuns
      .filter((r) => r.session_id === session.session_id)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
  }));

  const initViewport = () => {
    const allRuns = mockRuns;
    const initial = calculateFitAllViewport(allRuns, timelineWidth, 50);
    if (initial) setViewport(initial);
  };

  if (!viewport) {
    initViewport();
  }

  const handleZoom = (direction: 'in' | 'out') => {
    if (!viewport) return;
    const factor = direction === 'in' ? 1.5 : 0.67;
    const newPixelsPerMs = Math.max(
      1 / config.maxZoom,
      Math.min(1 / config.minZoom, viewport.pixelsPerMs * factor)
    );

    const viewportDuration = viewport.endTime.getTime() - viewport.startTime.getTime();
    const newDuration = viewportDuration / factor;
    const centerTime = new Date((viewport.startTime.getTime() + viewport.endTime.getTime()) / 2);

    setViewport({
      startTime: new Date(centerTime.getTime() - newDuration / 2),
      endTime: new Date(centerTime.getTime() + newDuration / 2),
      pixelsPerMs: newPixelsPerMs,
    });
  };

  const handleFitAll = () => {
    const allRuns = mockRuns;
    const newViewport = calculateFitAllViewport(allRuns, timelineWidth, 50);
    if (newViewport) setViewport(newViewport);
  };

  const handleJumpToNow = () => {
    if (!viewport) return;
    const viewportDuration = viewport.endTime.getTime() - viewport.startTime.getTime();
    const now = Date.now();
    setViewport({
      ...viewport,
      startTime: new Date(now - viewportDuration * 0.8),
      endTime: new Date(now + viewportDuration * 0.2),
    });
  };

  const handleRefresh = () => {
    initViewport();
  };

  const selectedRun = mockRuns.find((r) => r.run_id === selectedRunId);

  const activeSessions = mockSessions.filter((s) => s.status === 'running').length;
  const activeRuns = mockRuns.filter((r) => ['running', 'pending', 'claimed'].includes(r.status)).length;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <TimelineControls
        onZoomIn={() => handleZoom('in')}
        onZoomOut={() => handleZoom('out')}
        onFitAll={handleFitAll}
        onJumpToNow={handleJumpToNow}
        onRefresh={handleRefresh}
      />

      <div className="flex-shrink-0 flex items-center gap-4 px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm text-gray-600">
        <span>{mockSessions.length} sessions</span>
        <span>•</span>
        <span>{mockRuns.length} runs</span>
        {activeSessions > 0 && (
          <>
            <span>•</span>
            <span className="text-emerald-600">{activeSessions} active sessions</span>
          </>
        )}
        {activeRuns > 0 && (
          <>
            <span>•</span>
            <span className="text-blue-600">{activeRuns} running</span>
          </>
        )}
      </div>

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 flex flex-col overflow-hidden">
          {viewport && (
            <>
              <TimelineHeader viewport={viewport} config={config} timelineWidth={timelineWidth} />
              <div className="flex-1 overflow-y-auto bg-white">
                {sessionsWithRuns.map(({ session, runs }) => (
                  <Swimlane
                    key={session.session_id}
                    session={session}
                    runs={runs}
                    viewport={viewport}
                    config={config}
                    timelineWidth={timelineWidth}
                    selectedRunId={selectedRunId}
                    hoveredRunId={hoveredRunId}
                    onSelectRun={setSelectedRunId}
                    onHoverRun={setHoveredRunId}
                  />
                ))}
              </div>
            </>
          )}
        </div>

        {selectedRun && (
          <RunDetailPanel run={selectedRun} onClose={() => setSelectedRunId(null)} />
        )}
      </div>
    </div>
  );
}
