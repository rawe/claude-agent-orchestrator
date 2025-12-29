import { useState, useMemo } from 'react';
import { Badge, StatusBadge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import {
  Clock,
  Search,
  Filter,
  ExternalLink,
  Bot,
  Folder,
  Zap,
  Loader2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { useUnifiedView, useUnifiedSessionEvents } from '@/hooks';
import {
  type UnifiedRun,
  type UnifiedEvent,
  RunTypeValues,
  RunStatusValues,
  isRunActive,
} from '@/services';
import { formatRelativeTime, formatDuration, getEventTypeStyles } from './utils';

interface RunListItemProps {
  run: UnifiedRun;
  isSelected: boolean;
  onSelect: () => void;
}

function RunListItem({ run, isSelected, onSelect }: RunListItemProps) {
  const isActive = isRunActive(run.status);
  const isStartRun = run.type === RunTypeValues.START_SESSION;

  const getRunDuration = () => {
    if (!run.startedAt) return 'queued';
    const start = new Date(run.startedAt).getTime();
    const end = run.completedAt ? new Date(run.completedAt).getTime() : Date.now();
    return formatDuration(end - start);
  };

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
        <span className="font-mono text-xs text-gray-500">{run.runId.slice(0, 8)}</span>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-medium text-gray-900 truncate">{run.agentName ?? 'Unknown Agent'}</span>
        <Badge variant={isStartRun ? 'info' : 'default'} size="sm">
          {isStartRun ? 'start' : 'resume'}
        </Badge>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {getRunDuration()}
            {isActive && (
              <span className="relative flex h-1.5 w-1.5 ml-1">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
              </span>
            )}
          </span>
        </div>
        <span>{formatRelativeTime(run.createdAt)}</span>
      </div>
    </button>
  );
}

interface RunHistoryChipProps {
  run: UnifiedRun;
  index: number;
  isSelected: boolean;
  onClick: () => void;
}

function RunHistoryChip({ run, index, isSelected, onClick }: RunHistoryChipProps) {
  const isStartRun = run.type === RunTypeValues.START_SESSION;

  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700',
    claimed: 'bg-blue-100 text-blue-700',
    running: 'bg-emerald-100 text-emerald-700',
    stopping: 'bg-amber-100 text-amber-700',
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
      <span className="text-[10px] opacity-75">{isStartRun ? 'start' : 'resume'}</span>
    </button>
  );
}

/**
 * Filter events that occurred during a run's execution window
 */
function filterEventsForRun(events: UnifiedEvent[], run: UnifiedRun): UnifiedEvent[] {
  const runStart = run.startedAt ? new Date(run.startedAt).getTime() : null;
  const runEnd = run.completedAt ? new Date(run.completedAt).getTime() : null;

  if (!runStart) {
    return [];
  }

  return events.filter((event) => {
    const eventTime = new Date(event.timestamp).getTime();
    if (eventTime < runStart) return false;
    if (runEnd && eventTime > runEnd) return false;
    return true;
  });
}

export function RunCentricTab() {
  const { sessions, runs, runsBySession, sessionsById, loading, error, refresh, stats } = useUnifiedView();

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  // Auto-select first run when data loads
  if (!selectedRunId && runs.length > 0) {
    setSelectedRunId(runs[0].runId);
  }

  const selectedRun = runs.find((r) => r.runId === selectedRunId) ?? null;
  const selectedSession = selectedRun
    ? sessionsById.get(selectedRun.sessionId) ?? null
    : null;
  const sessionRuns = selectedRun
    ? (runsBySession.get(selectedRun.sessionId) ?? [])
        .slice()
        .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
    : [];

  // Fetch events for the selected run's session
  const { events, loading: eventsLoading } = useUnifiedSessionEvents(selectedRun?.sessionId ?? null);

  // Filter events for this run's time window
  const runEvents = selectedRun ? filterEventsForRun(events, selectedRun) : [];

  const filteredRuns = useMemo(() => {
    return runs
      .filter((r) => statusFilter === 'all' || r.status === statusFilter)
      .filter(
        (r) =>
          !search ||
          r.runId.toLowerCase().includes(search.toLowerCase()) ||
          (r.agentName?.toLowerCase().includes(search.toLowerCase()) ?? false)
      )
      .slice()
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [runs, statusFilter, search]);

  // Loading state
  if (loading && sessions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">Loading runs...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && sessions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-gray-700 font-medium mb-1">Failed to load data</p>
          <p className="text-gray-500 text-sm mb-4">{error}</p>
          <button
            onClick={refresh}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (runs.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Zap className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-700 font-medium mb-1">No runs yet</p>
          <p className="text-gray-500 text-sm">Runs will appear here when agents start executing.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex min-h-0">
      {/* Left: Run List */}
      <div className="w-96 border-r border-gray-200 bg-white flex-shrink-0 flex flex-col">
        <div className="p-3 border-b border-gray-200 space-y-3">
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
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1.5"
            >
              <option value="all">All Status</option>
              <option value={RunStatusValues.PENDING}>Pending</option>
              <option value={RunStatusValues.RUNNING}>Running</option>
              <option value={RunStatusValues.COMPLETED}>Completed</option>
              <option value={RunStatusValues.FAILED}>Failed</option>
              <option value={RunStatusValues.STOPPED}>Stopped</option>
            </select>
            <button
              onClick={refresh}
              disabled={loading}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {filteredRuns.map((run) => (
            <RunListItem
              key={run.runId}
              run={run}
              isSelected={selectedRunId === run.runId}
              onSelect={() => setSelectedRunId(run.runId)}
            />
          ))}
          {filteredRuns.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <p className="text-sm">No runs match your filters</p>
            </div>
          )}
        </div>

        <div className="px-3 py-2 border-t border-gray-200 text-xs text-gray-500">
          {filteredRuns.length} of {stats.totalRuns} runs
        </div>
      </div>

      {/* Right: Context Panel */}
      <div className="flex-1 flex flex-col min-w-0 bg-gray-50">
        {selectedRun && selectedSession ? (
          <>
            {/* Session Context Header */}
            <div className="flex-shrink-0 border-b border-gray-200 bg-white p-4 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-base font-semibold text-gray-900">{selectedSession.displayName}</h3>
                    <StatusBadge status={selectedSession.status} />
                  </div>
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <span className="font-mono">{selectedSession.sessionId.slice(0, 12)}...</span>
                    <ExternalLink className="w-3 h-3 ml-1 text-primary-600" />
                  </div>
                </div>
                <div className="text-right text-sm text-gray-500">
                  <div className="flex items-center gap-1.5 justify-end">
                    <Clock className="w-4 h-4" />
                    {formatRelativeTime(selectedSession.createdAt)}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4 text-sm">
                {selectedSession.agentName && (
                  <div className="flex items-center gap-1.5 text-gray-600">
                    <Bot className="w-4 h-4 text-gray-400" />
                    {selectedSession.agentName}
                  </div>
                )}
                {selectedSession.projectDir && (
                  <div className="flex items-center gap-1.5 text-gray-500">
                    <Folder className="w-4 h-4 text-gray-400" />
                    <span className="truncate max-w-[180px]">{selectedSession.projectDir.split('/').pop()}</span>
                  </div>
                )}
              </div>

              {/* Run History Chips */}
              <div>
                <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                  Run History ({sessionRuns.length})
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {sessionRuns.map((run, index) => (
                    <RunHistoryChip
                      key={run.runId}
                      run={run}
                      index={index + 1}
                      isSelected={run.runId === selectedRunId}
                      onClick={() => setSelectedRunId(run.runId)}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Run Events Stream */}
            <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
              <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <Zap className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">Run Events</span>
                  </div>
                  <Badge variant={selectedRun.type === RunTypeValues.START_SESSION ? 'info' : 'default'} size="sm">
                    {selectedRun.type === RunTypeValues.START_SESSION ? 'start' : 'resume'}
                  </Badge>
                  <RunStatusBadge status={selectedRun.status} />
                </div>
                <span className="text-sm text-gray-500">
                  {eventsLoading ? '...' : runEvents.length} events
                </span>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {eventsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                  </div>
                ) : runEvents.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <p className="text-sm">No events recorded for this run</p>
                  </div>
                ) : (
                  <div className="space-y-2 pl-4 border-l-2 border-gray-200">
                    {runEvents.map((event) => (
                      <div key={event.id} className="flex items-start gap-3 py-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-gray-400 mt-2 -ml-[0.45rem]" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs px-2 py-0.5 rounded border ${getEventTypeStyles(event.eventType)}`}>
                              {event.eventType}
                            </span>
                            <span className="text-xs text-gray-400 font-mono">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700">{event.summary}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Zap className="w-16 h-16 mx-auto text-gray-300 mb-4" />
              <p className="text-lg font-medium">Select a run</p>
              <p className="text-sm mt-1">Choose a run from the list to view session context and events</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
