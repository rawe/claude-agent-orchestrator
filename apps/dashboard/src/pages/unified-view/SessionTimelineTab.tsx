import { useState } from 'react';
import { Badge, StatusBadge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import {
  Layers,
  Zap,
  PanelLeftClose,
  PanelLeft,
  ChevronDown,
  ChevronRight,
  Play,
  RotateCcw,
  Clock,
  Server,
  MessageSquare,
  Bot,
  Hash,
  Calendar,
  Loader2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { useUnifiedView, useUnifiedSessionEvents } from '@/hooks';
import {
  type UnifiedSession,
  type UnifiedRun,
  type UnifiedEvent,
  RunTypeValues,
  isRunActive,
} from '@/services';
import { formatRelativeTime, formatDuration, getEventTypeStyles } from './utils';

interface SessionCardWithRunsProps {
  session: UnifiedSession;
  isSelected: boolean;
  onSelect: () => void;
}

function SessionCardWithRuns({ session, isSelected, onSelect }: SessionCardWithRunsProps) {
  const isActive = session.status === 'running';

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 rounded-lg border transition-all ${
        isSelected
          ? 'border-primary-300 bg-primary-50 ring-1 ring-primary-200'
          : isActive
            ? 'border-emerald-200 bg-emerald-50/50 hover:border-emerald-300'
            : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <Bot className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <span className="text-sm font-medium text-gray-900 truncate">{session.displayName}</span>
        </div>
        <StatusBadge status={session.status} />
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
        {session.agentName && (
          <span className="flex items-center gap-1">
            <Hash className="w-3 h-3" />
            {session.agentName}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {formatRelativeTime(session.createdAt)}
        </span>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <div className="flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-gray-400" />
          <span className="text-xs font-medium text-gray-700">{session.runCount} runs</span>
        </div>
        <RunStatusBadge status={session.latestRunStatus} />
      </div>
    </button>
  );
}

interface RunBlockProps {
  run: UnifiedRun;
  defaultExpanded?: boolean;
}

function RunBlock({ run, defaultExpanded = false }: RunBlockProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [eventsExpanded, setEventsExpanded] = useState(true);
  const [showPrompt, setShowPrompt] = useState(false);

  // Fetch events for this run's session
  const { events, loading: eventsLoading } = useUnifiedSessionEvents(expanded ? run.sessionId : null);

  // Filter events for this run's time window
  const runEvents = filterEventsForRun(events, run);

  const isActive = isRunActive(run.status);
  const isStartRun = run.type === RunTypeValues.START_SESSION;
  const RunTypeIcon = isStartRun ? Play : RotateCcw;

  const getRunDuration = () => {
    if (!run.startedAt) return '-';
    const start = new Date(run.startedAt).getTime();
    const end = run.completedAt ? new Date(run.completedAt).getTime() : Date.now();
    return formatDuration(end - start);
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-sm border overflow-hidden ${
        isActive ? 'border-emerald-300 ring-1 ring-emerald-100' : 'border-gray-200'
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="text-gray-400">
          {expanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        </div>

        <div
          className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
            isStartRun ? 'bg-blue-100' : 'bg-amber-100'
          }`}
        >
          <RunTypeIcon
            className={`w-4 h-4 ${isStartRun ? 'text-blue-600' : 'text-amber-600'}`}
          />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">Run #{run.runNumber}</span>
            <Badge variant={isStartRun ? 'info' : 'default'} size="sm">
              {isStartRun ? 'start' : 'resume'}
            </Badge>
            <RunStatusBadge status={run.status} />
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {getRunDuration()}
            </span>
            {run.runnerId && (
              <span className="flex items-center gap-1">
                <Server className="w-3 h-3" />
                {run.runnerId.slice(0, 12)}...
              </span>
            )}
            <span>{formatRelativeTime(run.createdAt)}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <MessageSquare className="w-3.5 h-3.5" />
          {eventsLoading ? '...' : runEvents.length} events
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
              <span className="font-medium">Parameters</span>
            </button>
            {showPrompt && (
              <div className="mt-2 p-3 bg-white rounded border border-gray-200">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                  {typeof run.parameters?.prompt === 'string'
                    ? run.parameters.prompt
                    : JSON.stringify(run.parameters, null, 2)}
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
              <>
                {eventsLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                  </div>
                ) : runEvents.length === 0 ? (
                  <div className="text-sm text-gray-500 py-2">No events recorded</div>
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
              </>
            )}
          </div>

          <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
            <span className="font-mono">{run.runId}</span>
          </div>
        </div>
      )}
    </div>
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

export function SessionTimelineTab() {
  const { sessions, runsBySession, loading, error, refresh, stats } = useUnifiedView();

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sidebarVisible, setSidebarVisible] = useState(true);

  // Auto-select first session when data loads
  if (!selectedSessionId && sessions.length > 0) {
    setSelectedSessionId(sessions[0].sessionId);
  }

  const selectedSession = sessions.find((s) => s.sessionId === selectedSessionId) ?? null;
  const sessionRuns = selectedSessionId
    ? (runsBySession.get(selectedSessionId) ?? [])
        .slice()
        .sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())
    : [];

  // Loading state
  if (loading && sessions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">Loading sessions...</p>
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
  if (sessions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Layers className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-700 font-medium mb-1">No sessions yet</p>
          <p className="text-gray-500 text-sm">Sessions and runs will appear here when agents start executing.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex min-h-0">
      {sidebarVisible && (
        <div className="w-80 border-r border-gray-200 bg-white flex-shrink-0 flex flex-col">
          <div className="p-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Sessions ({stats.totalSessions})
            </h3>
            <button
              onClick={refresh}
              disabled={loading}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {sessions.map((session) => (
              <SessionCardWithRuns
                key={session.sessionId}
                session={session}
                isSelected={selectedSessionId === session.sessionId}
                onSelect={() => setSelectedSessionId(session.sessionId)}
              />
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 bg-gray-50 flex flex-col min-w-0 overflow-hidden">
        <div className="flex-shrink-0 bg-white border-b border-gray-200 px-3 py-2 flex items-center justify-between">
          <button
            onClick={() => setSidebarVisible(!sidebarVisible)}
            className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {sidebarVisible ? (
              <>
                <PanelLeftClose className="w-4 h-4" />
                <span>Hide Sessions</span>
              </>
            ) : (
              <>
                <PanelLeft className="w-4 h-4" />
                <span>Show Sessions</span>
              </>
            )}
          </button>
        </div>

        {selectedSession && (
          <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900">{selectedSession.displayName}</h2>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    {selectedSession.agentName && (
                      <>
                        <span>Agent: {selectedSession.agentName}</span>
                        <span>-</span>
                      </>
                    )}
                    <span>Created {formatRelativeTime(selectedSession.createdAt)}</span>
                  </div>
                </div>
              </div>
              <StatusBadge status={selectedSession.status} />
            </div>
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-y-auto">
          {selectedSessionId ? (
            <div className="p-4 space-y-4">
              {sessionRuns.length === 0 ? (
                <div className="text-center py-12">
                  <Zap className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No runs for this session yet</p>
                </div>
              ) : (
                sessionRuns.map((run, index) => (
                  <RunBlock key={run.runId} run={run} defaultExpanded={index === 0} />
                ))
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <div className="text-gray-400 mb-4">
                  <Layers className="w-16 h-16" />
                </div>
                <h3 className="text-sm font-medium text-gray-900">Select a session</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Choose a session from the list to view its timeline with run blocks
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
