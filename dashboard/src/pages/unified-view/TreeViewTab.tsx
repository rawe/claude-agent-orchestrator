import { useState, useEffect, useCallback } from 'react';
import { Badge, StatusBadge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import {
  ChevronDown,
  ChevronRight,
  Play,
  RotateCcw,
  Bot,
  GitBranch,
  ChevronsUpDown,
  ChevronsDownUp,
  X,
  Zap,
  Loader2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { useUnifiedView, useUnifiedSessionEvents } from '@/hooks';
import {
  type SessionTreeNode,
  type UnifiedSession,
  type UnifiedRun,
  type UnifiedEvent,
  RunTypeValues,
  isRunActive,
} from '@/services';
import { formatRelativeTime, formatDuration, getEventTypeStyles } from './utils';

// ============================================================================
// APPROACH 3: TREE VIEW TAB (Real Data Implementation)
// ============================================================================

interface SessionTreeNodeProps {
  node: SessionTreeNode;
  depth: number;
  expandState: Record<string, boolean>;
  onToggle: (sessionId: string) => void;
  selectedId: string | null;
  onSelect: (type: 'session' | 'run', id: string, sessionId: string) => void;
}

function SessionTreeNodeComponent({
  node,
  depth,
  expandState,
  onToggle,
  selectedId,
  onSelect,
}: SessionTreeNodeProps) {
  const { session, runs, children } = node;
  const isExpanded = expandState[session.sessionId] ?? true;
  const isSelected = selectedId === session.sessionId;
  const hasActiveRun = runs.some((r) => isRunActive(r.status));

  const accentColor =
    session.status === 'running'
      ? 'border-l-emerald-500'
      : session.status === 'stopped'
        ? 'border-l-red-500'
        : 'border-l-gray-300';

  return (
    <div className="relative">
      {/* Session Node */}
      <div
        className={`relative flex items-start gap-2 p-3 rounded-lg border-l-4 transition-colors cursor-pointer mb-1 ${accentColor} ${
          isSelected
            ? 'bg-primary-50 ring-2 ring-primary-500 border-gray-200'
            : 'bg-white hover:bg-gray-50 border border-gray-200'
        }`}
        style={{ marginLeft: `${depth * 24}px` }}
        onClick={() => onSelect('session', session.sessionId, session.sessionId)}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle(session.sessionId);
          }}
          className="flex-shrink-0 p-1 hover:bg-gray-100 rounded"
        >
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        <div
          className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
            hasActiveRun ? 'bg-emerald-100' : 'bg-gray-100'
          }`}
        >
          <GitBranch className={`w-4 h-4 ${hasActiveRun ? 'text-emerald-600' : 'text-gray-600'}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-gray-900 truncate">{session.displayName}</span>
            <StatusBadge status={session.status} />
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-500">
            {session.agentName && (
              <span className="flex items-center gap-1">
                <Bot className="w-3 h-3" />
                {session.agentName}
              </span>
            )}
            <span>{runs.length} runs</span>
            {children.length > 0 && <span>{children.length} children</span>}
          </div>

          <div className="mt-1 text-xs text-gray-400">{formatRelativeTime(session.createdAt)}</div>
        </div>
      </div>

      {/* Expanded content: runs and children */}
      {isExpanded && (
        <div className="space-y-1">
          {/* Runs */}
          {runs.map((run) => (
            <RunTreeNodeComponent
              key={run.runId}
              run={run}
              depth={depth + 1}
              isSelected={selectedId === run.runId}
              onSelect={() => onSelect('run', run.runId, run.sessionId)}
            />
          ))}

          {/* Child sessions */}
          {children.map((childNode) => (
            <SessionTreeNodeComponent
              key={childNode.session.sessionId}
              node={childNode}
              depth={depth + 1}
              expandState={expandState}
              onToggle={onToggle}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface RunTreeNodeProps {
  run: UnifiedRun;
  depth: number;
  isSelected: boolean;
  onSelect: () => void;
}

function RunTreeNodeComponent({ run, depth, isSelected, onSelect }: RunTreeNodeProps) {
  const isActive = isRunActive(run.status);
  const isStartRun = run.type === RunTypeValues.START_SESSION;
  const TypeIcon = isStartRun ? Play : RotateCcw;

  const getDuration = () => {
    if (!run.startedAt) return '-';
    const start = new Date(run.startedAt).getTime();
    const end = run.completedAt ? new Date(run.completedAt).getTime() : Date.now();
    return formatDuration(end - start);
  };

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-md transition-colors cursor-pointer ${
        isSelected ? 'bg-primary-50 ring-1 ring-primary-400' : 'bg-white hover:bg-gray-50 border border-gray-100'
      }`}
      style={{ marginLeft: `${depth * 24 + 12}px` }}
      onClick={onSelect}
    >
      <div className="w-4 h-px bg-gray-300" />

      <div className={`flex-shrink-0 w-6 h-6 rounded flex items-center justify-center ${isActive ? 'bg-blue-100' : 'bg-gray-100'}`}>
        <Zap className={`w-3 h-3 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
      </div>

      <div className="flex-1 min-w-0 flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Run #{run.runNumber}</span>
        <Badge variant={isStartRun ? 'info' : 'default'} size="sm">
          <TypeIcon className="w-3 h-3 mr-1" />
          {isStartRun ? 'start' : 'resume'}
        </Badge>
        <RunStatusBadge status={run.status} />
        <span className="text-xs text-gray-500">{getDuration()}</span>
      </div>

      <span className="text-xs text-gray-400 font-mono">{run.runId.slice(0, 12)}</span>
    </div>
  );
}

interface TreeDetailPanelProps {
  type: 'session' | 'run';
  session: UnifiedSession | null;
  run: UnifiedRun | null;
  sessionRuns: UnifiedRun[];
  onClose: () => void;
}

function TreeDetailPanel({ type, session, run, sessionRuns, onClose }: TreeDetailPanelProps) {
  // Fetch events for the selected session
  const sessionIdForEvents = type === 'session' ? session?.sessionId : run?.sessionId;
  const { events, loading: eventsLoading } = useUnifiedSessionEvents(sessionIdForEvents ?? null);

  if (type === 'session' && session) {
    return (
      <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Session Details</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-lg font-medium text-gray-900">{session.displayName}</h4>
              <StatusBadge status={session.status} />
            </div>
            <div className="text-xs text-gray-500 font-mono mb-3">{session.sessionId}</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {session.agentName && (
                <div>
                  <span className="text-gray-500">Agent:</span>
                  <span className="ml-2 text-gray-900">{session.agentName}</span>
                </div>
              )}
              <div>
                <span className="text-gray-500">Runs:</span>
                <span className="ml-2 text-gray-900">{sessionRuns.length}</span>
              </div>
              <div>
                <span className="text-gray-500">Created:</span>
                <span className="ml-2 text-gray-900">{formatRelativeTime(session.createdAt)}</span>
              </div>
              {session.parentSessionId && (
                <div>
                  <span className="text-gray-500">Parent:</span>
                  <span className="ml-2 text-gray-900 font-mono text-xs">{session.parentSessionId.slice(0, 16)}...</span>
                </div>
              )}
              {session.hostname && (
                <div>
                  <span className="text-gray-500">Host:</span>
                  <span className="ml-2 text-gray-900">{session.hostname}</span>
                </div>
              )}
              {session.executorProfile && (
                <div>
                  <span className="text-gray-500">Profile:</span>
                  <span className="ml-2 text-gray-900">{session.executorProfile}</span>
                </div>
              )}
            </div>
          </div>

          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Runs ({sessionRuns.length})</h5>
            <div className="space-y-2">
              {sessionRuns.map((r) => (
                <div key={r.runId} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                  <span className="text-sm font-medium">#{r.runNumber}</span>
                  <Badge variant={r.type === RunTypeValues.START_SESSION ? 'info' : 'default'} size="sm">
                    {r.type === RunTypeValues.START_SESSION ? 'start' : 'resume'}
                  </Badge>
                  <RunStatusBadge status={r.status} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === 'run' && run) {
    // Filter events for this run's time window
    const runEvents = filterEventsForRun(events, run);

    return (
      <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Run Details</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-lg font-medium text-gray-900">Run #{run.runNumber}</h4>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="text-xs text-gray-500 font-mono mb-3">{run.runId}</div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant={run.type === RunTypeValues.START_SESSION ? 'info' : 'default'} size="sm">
                  {run.type === RunTypeValues.START_SESSION ? 'start' : 'resume'}
                </Badge>
                {run.agentName && (
                  <>
                    <span className="text-gray-500">•</span>
                    <span className="text-gray-900">{run.agentName}</span>
                  </>
                )}
              </div>
              <div>
                <span className="text-gray-500">Created:</span>
                <span className="ml-2 text-gray-900">{formatRelativeTime(run.createdAt)}</span>
              </div>
              {run.error && (
                <div className="p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">
                  {run.error}
                </div>
              )}
            </div>
          </div>

          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Prompt</h5>
            <div className="p-2 bg-gray-50 rounded text-sm text-gray-700 max-h-32 overflow-y-auto">
              {run.prompt}
            </div>
          </div>

          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">
              Events ({eventsLoading ? '...' : runEvents.length})
            </h5>
            {eventsLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
              </div>
            ) : runEvents.length === 0 ? (
              <div className="text-sm text-gray-500 py-2">No events recorded</div>
            ) : (
              <div className="space-y-2 pl-3 border-l-2 border-gray-200">
                {runEvents.map((event) => (
                  <div key={event.id} className="py-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`text-xs px-1.5 py-0.5 rounded border ${getEventTypeStyles(event.eventType)}`}>
                        {event.eventType}
                      </span>
                      <span className="text-xs text-gray-400 font-mono">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{event.summary}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
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

export function TreeViewTab() {
  const { sessions, runs, sessionTree, runsBySession, sessionsById, loading, error, refresh, stats } = useUnifiedView();

  const [expandState, setExpandState] = useState<Record<string, boolean>>({});
  const [selectedItem, setSelectedItem] = useState<{
    type: 'session' | 'run';
    id: string;
    sessionId: string;
  } | null>(null);

  // Initialize expand state when sessions change
  useEffect(() => {
    const initial: Record<string, boolean> = {};
    sessions.forEach((s) => {
      // Expand root sessions by default, collapse children
      initial[s.sessionId] = s.parentSessionId === null;
    });
    setExpandState((prev) => {
      // Preserve existing expand state for known sessions
      const merged = { ...initial };
      for (const key of Object.keys(prev)) {
        if (key in merged) {
          merged[key] = prev[key];
        }
      }
      return merged;
    });
  }, [sessions]);

  const toggleNode = useCallback((sessionId: string) => {
    setExpandState((prev) => ({ ...prev, [sessionId]: !prev[sessionId] }));
  }, []);

  const expandAll = useCallback(() => {
    const newState: Record<string, boolean> = {};
    sessions.forEach((s) => {
      newState[s.sessionId] = true;
    });
    setExpandState(newState);
  }, [sessions]);

  const collapseAll = useCallback(() => {
    const newState: Record<string, boolean> = {};
    sessions.forEach((s) => {
      newState[s.sessionId] = false;
    });
    setExpandState(newState);
  }, [sessions]);

  const handleSelect = useCallback((type: 'session' | 'run', id: string, sessionId: string) => {
    setSelectedItem({ type, id, sessionId });
  }, []);

  // Get selected items
  const selectedSession = selectedItem?.type === 'session'
    ? sessionsById.get(selectedItem.id) ?? null
    : null;
  const selectedRun = selectedItem?.type === 'run'
    ? runs.find((r) => r.runId === selectedItem.id) ?? null
    : null;
  const selectedSessionRuns = selectedItem
    ? runsBySession.get(selectedItem.sessionId) ?? []
    : [];

  // Loading state
  if (loading && sessions.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">Loading sessions and runs...</p>
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
          <GitBranch className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-700 font-medium mb-1">No sessions yet</p>
          <p className="text-gray-500 text-sm">Sessions and runs will appear here when agents start executing.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>{stats.totalSessions} sessions</span>
          <span>•</span>
          <span>{stats.totalRuns} runs</span>
          {stats.activeSessions > 0 && (
            <>
              <span>•</span>
              <span className="text-emerald-600">{stats.activeSessions} active sessions</span>
            </>
          )}
          {stats.activeRuns > 0 && (
            <>
              <span>•</span>
              <span className="text-blue-600">{stats.activeRuns} running</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={expandAll}
            className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded"
            title="Expand all"
          >
            <ChevronsDownUp className="w-4 h-4" />
            Expand
          </button>
          <button
            onClick={collapseAll}
            className="flex items-center gap-1.5 px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded"
            title="Collapse all"
          >
            <ChevronsUpDown className="w-4 h-4" />
            Collapse
          </button>
        </div>
      </div>

      {/* Tree + Detail Panel */}
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 overflow-y-auto bg-gray-50 p-4">
          <div className="space-y-1">
            {sessionTree.map((node) => (
              <SessionTreeNodeComponent
                key={node.session.sessionId}
                node={node}
                depth={0}
                expandState={expandState}
                onToggle={toggleNode}
                selectedId={selectedItem?.id ?? null}
                onSelect={handleSelect}
              />
            ))}
          </div>
        </div>

        {selectedItem && (
          <TreeDetailPanel
            type={selectedItem.type}
            session={selectedSession}
            run={selectedRun}
            sessionRuns={selectedSessionRuns}
            onClose={() => setSelectedItem(null)}
          />
        )}
      </div>
    </div>
  );
}
