import { useState, useMemo } from 'react';
import { Badge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import {
  LayoutGrid,
  List,
  Search,
  RefreshCw,
  X,
  Clock,
  Activity,
  ChevronDown,
  ChevronRight,
  Play,
  RotateCcw,
  Users,
  Zap,
} from 'lucide-react';
import {
  MockSession,
  MockRun,
  mockSessions,
  mockRuns,
  formatRelativeTime,
  formatDuration,
  getEventTypeStyles,
} from './';

// ============================================================================
// TYPES
// ============================================================================

type LayoutMode = 'grid' | 'list';
type SortField = 'lastActivity' | 'runCount' | 'name' | 'status';
type StatusFilter = 'all' | 'running' | 'finished' | 'failed';
type DetailTab = 'overview' | 'runs' | 'events';

interface SessionWithRuns extends MockSession {
  runs: MockRun[];
  activeRunCount: number;
  lastRunAt: string | null;
  childSessionIds: string[];
}

interface SessionRunStats {
  totalRuns: number;
  completedRuns: number;
  failedRuns: number;
  runningRuns: number;
  totalDuration: number;
  averageDuration: number;
}

interface SparklineDataPoint {
  timestamp: number;
  value: number;
  status: 'pending' | 'claimed' | 'running' | 'stopping' | 'completed' | 'failed' | 'stopped';
  runId: string;
}

// ============================================================================
// DATA HELPERS
// ============================================================================

function buildSessionsWithRuns(): SessionWithRuns[] {
  // Create runs lookup by session_id
  const runsBySession = new Map<string, MockRun[]>();
  mockRuns.forEach((run) => {
    const list = runsBySession.get(run.session_id) || [];
    list.push(run);
    runsBySession.set(run.session_id, list);
  });
  // Sort runs by created_at
  runsBySession.forEach((list) => {
    list.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  });

  // Build child session lookup
  const childSessionsByParent = new Map<string, string[]>();
  mockSessions.forEach((s) => {
    if (s.parent_session_id) {
      const list = childSessionsByParent.get(s.parent_session_id) || [];
      list.push(s.session_id);
      childSessionsByParent.set(s.parent_session_id, list);
    }
  });

  // Merge sessions with runs
  return mockSessions.map((session) => {
    const sessionRuns = runsBySession.get(session.session_id) || [];
    const activeRuns = sessionRuns.filter((r) =>
      ['pending', 'claimed', 'running', 'stopping'].includes(r.status)
    );
    const lastRun = sessionRuns[sessionRuns.length - 1];

    return {
      ...session,
      runs: sessionRuns,
      activeRunCount: activeRuns.length,
      lastRunAt: lastRun?.created_at || null,
      childSessionIds: childSessionsByParent.get(session.session_id) || [],
    };
  });
}

function getSessionStats(session: SessionWithRuns): SessionRunStats | null {
  if (session.runs.length === 0) return null;

  const completed = session.runs.filter((r) => r.status === 'completed');
  const failed = session.runs.filter((r) => r.status === 'failed');
  const running = session.runs.filter((r) => r.status === 'running');

  const durations = session.runs
    .filter((r) => r.started_at && r.completed_at)
    .map((r) => new Date(r.completed_at!).getTime() - new Date(r.started_at!).getTime());

  const totalDuration = durations.reduce((a, b) => a + b, 0);

  return {
    totalRuns: session.runs.length,
    completedRuns: completed.length,
    failedRuns: failed.length,
    runningRuns: running.length,
    totalDuration,
    averageDuration: durations.length > 0 ? totalDuration / durations.length : 0,
  };
}

function getSparklineData(session: SessionWithRuns): SparklineDataPoint[] {
  if (session.runs.length === 0) return [];

  return session.runs.map((run) => ({
    timestamp: new Date(run.created_at).getTime(),
    value:
      run.completed_at && run.started_at
        ? new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
        : run.started_at
          ? Date.now() - new Date(run.started_at).getTime()
          : 30000, // Default 30s for pending
    status: run.status,
    runId: run.run_id,
  }));
}

const sessionsWithRuns = buildSessionsWithRuns();

// ============================================================================
// ACTIVITY SPARKLINE COMPONENT
// ============================================================================

const statusColors: Record<string, string> = {
  pending: '#9ca3af',
  claimed: '#9ca3af',
  running: '#10b981',
  stopping: '#f59e0b',
  completed: '#22c55e',
  failed: '#ef4444',
  stopped: '#6b7280',
};

interface ActivitySparklineProps {
  data: SparklineDataPoint[];
  height?: number;
}

function ActivitySparkline({ data, height = 32 }: ActivitySparklineProps) {
  const { points } = useMemo(() => {
    if (data.length === 0) return { points: '' };

    const sortedData = [...data].sort((a, b) => a.timestamp - b.timestamp);
    const minTime = sortedData[0].timestamp;
    const maxTime = sortedData[sortedData.length - 1].timestamp;
    const timeRange = maxTime - minTime || 1;

    const maxValue = Math.max(...sortedData.map((d) => d.value), 1);

    const pts = sortedData
      .map((d) => {
        const x = ((d.timestamp - minTime) / timeRange) * 100;
        const y = height - (d.value / maxValue) * (height - 4);
        return `${x},${y}`;
      })
      .join(' ');

    return { points: pts };
  }, [data, height]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-400" style={{ height }}>
        No activity
      </div>
    );
  }

  const sortedData = [...data].sort((a, b) => a.timestamp - b.timestamp);
  const minTime = sortedData[0].timestamp;
  const maxTime = sortedData[sortedData.length - 1].timestamp;
  const timeRange = maxTime - minTime || 1;
  const maxValue = Math.max(...sortedData.map((d) => d.value), 1);

  return (
    <svg
      viewBox={`0 0 100 ${height}`}
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
      {data.map((d) => {
        const x = ((d.timestamp - minTime) / timeRange) * 100;
        const y = height - (d.value / maxValue) * (height - 4);

        return (
          <circle key={d.runId} cx={x} cy={y} r="3" fill={statusColors[d.status] || '#3b82f6'} />
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

// ============================================================================
// SESSION CARD COMPONENT
// ============================================================================

interface SessionCardProps {
  session: SessionWithRuns;
  isSelected: boolean;
  onClick: () => void;
  sparklineData: SparklineDataPoint[];
  variant?: 'grid' | 'list';
}

function SessionCard({
  session,
  isSelected,
  onClick,
  sparklineData,
  variant = 'grid',
}: SessionCardProps) {
  const hasActiveRuns = session.activeRunCount > 0;
  const hasFailed = session.runs.some((r) => r.status === 'failed');

  const runSummary = useMemo(() => {
    if (session.runCount === 0) return 'No runs';
    if (hasActiveRuns) return `${session.runCount} runs (${session.activeRunCount} active)`;
    return `${session.runCount} runs`;
  }, [session.runCount, session.activeRunCount, hasActiveRuns]);

  const getStatusBadgeVariant = (status: MockSession['status']) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'finished':
        return 'default';
      case 'stopped':
        return 'warning';
      default:
        return 'default';
    }
  };

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
            <span className="font-medium text-gray-900 truncate">{session.name}</span>
            <Badge variant={getStatusBadgeVariant(session.status)} size="sm">
              {session.status}
            </Badge>
            {hasActiveRuns && (
              <span className="flex h-2 w-2 relative">
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
          <h3 className="font-medium text-gray-900 truncate">{session.name}</h3>
          {session.agent_name && (
            <p className="text-sm text-gray-500 truncate">{session.agent_name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={getStatusBadgeVariant(session.status)} size="sm">
            {session.status}
          </Badge>
          {hasActiveRuns && (
            <span className="flex h-2 w-2 relative">
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
              {mockSessions.find((s) => s.session_id === session.parent_session_id)?.name ||
                session.parent_session_id.slice(0, 12) + '...'}
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

// ============================================================================
// TAB HEADER COMPONENT
// ============================================================================

interface TabHeaderProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  statusFilter: StatusFilter;
  onStatusFilterChange: (value: StatusFilter) => void;
  sortField: SortField;
  onSortChange: (value: SortField) => void;
  layout: LayoutMode;
  onLayoutChange: (value: LayoutMode) => void;
  onRefresh: () => void;
  sessionCount: number;
}

function TabHeader({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  sortField,
  onSortChange,
  layout,
  onLayoutChange,
  onRefresh,
  sessionCount,
}: TabHeaderProps) {
  return (
    <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        {/* Left side: Search and filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-lg w-64 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value as StatusFilter)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-2"
          >
            <option value="all">All Status</option>
            <option value="running">Running</option>
            <option value="finished">Finished</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={sortField}
            onChange={(e) => onSortChange(e.target.value as SortField)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-2"
          >
            <option value="lastActivity">Last Activity</option>
            <option value="runCount">Run Count</option>
            <option value="name">Name</option>
            <option value="status">Status</option>
          </select>
        </div>

        {/* Right side: Layout toggle and refresh */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{sessionCount} sessions</span>

          <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
            <button
              onClick={() => onLayoutChange('grid')}
              className={`p-2 transition-colors ${
                layout === 'grid' ? 'bg-primary-100 text-primary-700' : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              title="Grid view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => onLayoutChange('list')}
              className={`p-2 transition-colors ${
                layout === 'list' ? 'bg-primary-100 text-primary-700' : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
              title="List view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={onRefresh}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// SESSION DETAIL PANEL COMPONENT
// ============================================================================

interface SessionDetailPanelProps {
  session: SessionWithRuns;
  stats: SessionRunStats | null;
  onClose: () => void;
}

function SessionDetailPanel({ session, stats, onClose }: SessionDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [expandedRunIds, setExpandedRunIds] = useState<Set<string>>(new Set());

  const toggleRunExpanded = (runId: string) => {
    setExpandedRunIds((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  };

  const getStatusBadgeVariant = (status: MockSession['status']) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'finished':
        return 'default';
      case 'stopped':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-[480px] bg-white shadow-xl border-l border-gray-200 z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{session.name}</h2>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={getStatusBadgeVariant(session.status)} size="sm">
              {session.status}
            </Badge>
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
          { id: 'overview' as DetailTab, label: 'Overview', icon: Activity },
          { id: 'runs' as DetailTab, label: 'Runs', icon: Zap },
          { id: 'events' as DetailTab, label: 'Events', icon: Clock },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium
              transition-colors border-b-2 -mb-px
              ${
                activeTab === id
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
                  <dd className="font-mono text-gray-900 text-xs">{session.session_id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Created</dt>
                  <dd className="text-gray-900">{formatRelativeTime(session.created_at)}</dd>
                </div>
                {session.project_dir && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Project</dt>
                    <dd className="font-mono text-gray-900 text-xs truncate max-w-[200px]">
                      {session.project_dir}
                    </dd>
                  </div>
                )}
                {session.parent_session_id && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Parent</dt>
                    <dd className="font-mono text-gray-900 text-xs truncate max-w-[200px]">
                      {mockSessions.find((s) => s.session_id === session.parent_session_id)?.name ||
                        session.parent_session_id}
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

            {/* Activity Sparkline */}
            <section>
              <h3 className="text-sm font-medium text-gray-900 mb-3">Activity Timeline</h3>
              <div className="bg-gray-50 rounded-lg p-3">
                <ActivitySparkline data={getSparklineData(session)} height={48} />
              </div>
            </section>
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="space-y-3">
            {session.runs.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Zap className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                <p>No runs yet</p>
              </div>
            ) : (
              session.runs.map((run) => {
                const isExpanded = expandedRunIds.has(run.run_id);
                const duration =
                  run.started_at && run.completed_at
                    ? formatDuration(
                        new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()
                      )
                    : run.started_at
                      ? 'Running...'
                      : 'Pending';

                return (
                  <div
                    key={run.run_id}
                    className="border border-gray-200 rounded-lg bg-white overflow-hidden"
                  >
                    <button
                      onClick={() => toggleRunExpanded(run.run_id)}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-shrink-0">
                        {run.type === 'start_session' ? (
                          <Play className="w-4 h-4 text-blue-500" />
                        ) : (
                          <RotateCcw className="w-4 h-4 text-purple-500" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">Run #{run.runNumber}</span>
                          <RunStatusBadge status={run.status} />
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {formatRelativeTime(run.created_at)} | {duration}
                        </div>
                      </div>
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                    </button>

                    {isExpanded && (
                      <div className="px-4 pb-4 border-t border-gray-100">
                        <div className="mt-3 space-y-3">
                          <div>
                            <div className="text-xs text-gray-500 uppercase mb-1">Prompt</div>
                            <div className="bg-gray-50 rounded-lg p-3 max-h-24 overflow-y-auto">
                              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                                {run.prompt}
                              </pre>
                            </div>
                          </div>

                          {run.error && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                              <p className="text-sm text-red-700">{run.error}</p>
                            </div>
                          )}

                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <span className="text-gray-500">Type:</span>{' '}
                              <span className="font-medium">{run.type}</span>
                            </div>
                            <div>
                              <span className="text-gray-500">Events:</span>{' '}
                              <span className="font-medium">{run.events.length}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2">
            {session.runs.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Clock className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                <p>No events yet</p>
              </div>
            ) : (
              session.runs.flatMap((run) =>
                run.events.map((event, idx) => (
                  <div
                    key={`${run.run_id}-event-${idx}`}
                    className="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg"
                  >
                    <div
                      className={`px-2 py-1 text-xs rounded border ${getEventTypeStyles(event.type)}`}
                    >
                      {event.type}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900">{event.summary}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Run #{run.runNumber} at {event.timestamp}
                      </p>
                    </div>
                  </div>
                ))
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function DashboardCardsTab() {
  const [layout, setLayout] = useState<LayoutMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortField, setSortField] = useState<SortField>('lastActivity');
  const [selectedSession, setSelectedSession] = useState<SessionWithRuns | null>(null);

  // Filter and sort sessions
  const filteredSessions = useMemo(() => {
    let result = [...sessionsWithRuns];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.session_id.toLowerCase().includes(query) ||
          s.name.toLowerCase().includes(query) ||
          s.agent_name?.toLowerCase().includes(query)
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      result = result.filter((s) => {
        if (statusFilter === 'running') return s.activeRunCount > 0 || s.status === 'running';
        if (statusFilter === 'finished') return s.status === 'finished';
        if (statusFilter === 'failed') return s.runs.some((r) => r.status === 'failed');
        return true;
      });
    }

    // Sort
    result.sort((a, b) => {
      switch (sortField) {
        case 'lastActivity':
          return (
            new Date(b.lastRunAt || 0).getTime() - new Date(a.lastRunAt || 0).getTime()
          );
        case 'runCount':
          return b.runCount - a.runCount;
        case 'name':
          return a.name.localeCompare(b.name);
        case 'status':
          return a.status.localeCompare(b.status);
        default:
          return 0;
      }
    });

    return result;
  }, [searchQuery, statusFilter, sortField]);

  const handleRefresh = () => {
    // In a real implementation, this would refetch data
    console.log('Refreshing dashboard cards...');
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-gray-50">
      <TabHeader
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        sortField={sortField}
        onSortChange={setSortField}
        layout={layout}
        onLayoutChange={setLayout}
        onRefresh={handleRefresh}
        sessionCount={filteredSessions.length}
      />

      <div className="flex-1 overflow-auto p-4">
        {filteredSessions.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No sessions found</h3>
            <p className="text-sm text-gray-500 mt-1">
              Try adjusting your search or filters
            </p>
          </div>
        ) : layout === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredSessions.map((session) => (
              <SessionCard
                key={session.session_id}
                session={session}
                isSelected={selectedSession?.session_id === session.session_id}
                onClick={() => setSelectedSession(session)}
                sparklineData={getSparklineData(session)}
                variant="grid"
              />
            ))}
          </div>
        ) : (
          <div className="space-y-3 max-w-4xl">
            {filteredSessions.map((session) => (
              <SessionCard
                key={session.session_id}
                session={session}
                isSelected={selectedSession?.session_id === session.session_id}
                onClick={() => setSelectedSession(session)}
                sparklineData={getSparklineData(session)}
                variant="list"
              />
            ))}
          </div>
        )}
      </div>

      {selectedSession && (
        <SessionDetailPanel
          session={selectedSession}
          stats={getSessionStats(selectedSession)}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  );
}
