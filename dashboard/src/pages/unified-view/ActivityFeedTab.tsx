import { useState } from 'react';
import { Badge } from '@/components/common';
import { RunStatusBadge } from '@/components/features/runs';
import {
  Zap,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Activity,
  CheckCircle2,
  XCircle,
  StopCircle,
  Loader2,
} from 'lucide-react';
import {
  MockRun,
  ActivityType,
  ActivityItem,
  RunActivityItem,
  EventActivityItem,
  mockSessions,
  mockRuns,
  formatRelativeTime,
  formatDuration,
  getEventTypeStyles,
} from './';

// Generate mock activity items from runs and events
function generateMockActivities(): ActivityItem[] {
  const activities: ActivityItem[] = [];

  // Generate run lifecycle activities
  mockRuns.forEach((run) => {
    const session = mockSessions.find((s) => s.session_id === run.session_id);
    const sessionName = session?.name || 'Unknown Session';
    const agentName = run.agent_name;

    // Run started
    if (run.started_at) {
      activities.push({
        id: `run-started-${run.run_id}`,
        timestamp: run.started_at,
        type: 'run_started',
        sessionId: run.session_id,
        sessionName,
        agentName,
        run,
        runNumber: run.runNumber,
      });
    }

    // Run completed/failed/stopped
    if (run.completed_at) {
      // Cast to avoid TypeScript narrowing based on literal types in mock data
      const status = run.status as MockRun['status'];
      let activityType: 'run_failed' | 'run_stopped' | 'run_completed' = 'run_completed';
      if (status === 'failed') {
        activityType = 'run_failed';
      } else if (status === 'stopped') {
        activityType = 'run_stopped';
      }
      activities.push({
        id: `run-${activityType}-${run.run_id}`,
        timestamp: run.completed_at,
        type: activityType,
        sessionId: run.session_id,
        sessionName,
        agentName,
        run,
        runNumber: run.runNumber,
      });
    }

    // Session events from run events
    run.events.forEach((event, index) => {
      const eventTime = new Date(run.started_at || run.created_at);
      // Parse timestamp like "10:00:45" and add offset
      const [hours, minutes, seconds] = event.timestamp.split(':').map(Number);
      eventTime.setHours(hours, minutes, seconds);

      activities.push({
        id: `event-${run.run_id}-${index}`,
        timestamp: eventTime.toISOString(),
        type: 'session_event',
        sessionId: run.session_id,
        sessionName,
        agentName,
        eventType: event.type,
        summary: event.summary,
        runId: run.run_id,
      });
    });
  });

  // Sort by timestamp descending (newest first)
  return activities.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
}

const mockActivities = generateMockActivities();

// Activity type configuration
const ACTIVITY_TYPE_CONFIG = {
  run_started: {
    icon: Zap,
    label: 'RUN STARTED',
    color: 'blue',
    emoji: '🚀',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    borderColor: 'border-l-blue-500',
  },
  run_completed: {
    icon: CheckCircle2,
    label: 'RUN COMPLETED',
    color: 'emerald',
    emoji: '✅',
    bgColor: 'bg-emerald-100',
    textColor: 'text-emerald-700',
    borderColor: 'border-l-emerald-500',
  },
  run_failed: {
    icon: XCircle,
    label: 'RUN FAILED',
    color: 'red',
    emoji: '❌',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700',
    borderColor: 'border-l-red-500',
  },
  run_stopped: {
    icon: StopCircle,
    label: 'RUN STOPPED',
    color: 'gray',
    emoji: '⏹️',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
    borderColor: 'border-l-gray-500',
  },
  session_event: {
    icon: MessageSquare,
    label: 'EVENT',
    color: 'purple',
    emoji: '🔧',
    bgColor: 'bg-purple-100',
    textColor: 'text-purple-700',
    borderColor: 'border-l-purple-500',
  },
};

interface ActivityCardProps {
  activity: ActivityItem;
  expanded: boolean;
  onToggle: () => void;
  animate?: boolean;
}

function ActivityCard({ activity, expanded, onToggle, animate }: ActivityCardProps) {
  const config = ACTIVITY_TYPE_CONFIG[activity.type];
  const Icon = config.icon;

  const isRunActivity = (a: ActivityItem): a is RunActivityItem =>
    ['run_started', 'run_completed', 'run_failed', 'run_stopped'].includes(a.type);

  const getDuration = (run: MockRun) => {
    if (!run.started_at || !run.completed_at) return '-';
    const ms = new Date(run.completed_at).getTime() - new Date(run.started_at).getTime();
    return formatDuration(ms);
  };

  return (
    <div
      className={`bg-white rounded-lg border border-gray-200 border-l-4 ${config.borderColor} shadow-sm transition-all ${
        animate ? 'animate-pulse' : ''
      }`}
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        <div className={`w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-4 h-4 ${config.textColor}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs font-bold uppercase ${config.textColor}`}>
              {config.emoji} {config.label}
            </span>
            <span className="text-xs text-gray-400">{formatRelativeTime(activity.timestamp)}</span>
          </div>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {isRunActivity(activity) ? (
              <>
                <span className="text-sm font-medium text-gray-900">
                  Run #{activity.runNumber} of {activity.sessionName}
                </span>
                <Badge variant={activity.run.type === 'start_session' ? 'info' : 'default'} size="sm">
                  {activity.run.type === 'start_session' ? 'start' : 'resume'}
                </Badge>
              </>
            ) : (
              <>
                <span className="text-sm font-medium text-gray-900">{activity.sessionName}</span>
                <span className="text-xs text-gray-500">→</span>
                <span className={`text-xs px-2 py-0.5 rounded border ${getEventTypeStyles(activity.eventType)}`}>
                  {activity.eventType}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {isRunActivity(activity) && <RunStatusBadge status={activity.run.status} />}
          {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="mt-3 space-y-3">
            {isRunActivity(activity) ? (
              <>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Agent:</span>{' '}
                    <span className="font-medium">{activity.agentName}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Duration:</span>{' '}
                    <span className="font-medium">{getDuration(activity.run)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Session:</span>{' '}
                    <span className="font-medium font-mono text-xs">{activity.sessionId.slice(0, 16)}...</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Run ID:</span>{' '}
                    <span className="font-medium font-mono text-xs">{activity.run.run_id.slice(0, 12)}...</span>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-gray-500 uppercase mb-1">Prompt</div>
                  <div className="bg-gray-50 rounded-lg p-3 max-h-32 overflow-y-auto">
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                      {activity.run.prompt.slice(0, 300)}
                      {activity.run.prompt.length > 300 ? '...' : ''}
                    </pre>
                  </div>
                </div>

                {activity.run.error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-sm text-red-700">{activity.run.error}</p>
                  </div>
                )}
              </>
            ) : (
              <div className="text-sm text-gray-700">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-gray-500">Agent:</span>
                  <span className="font-medium">{activity.agentName}</span>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p>{activity.summary}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface FeedToolbarProps {
  selectedTypes: ActivityType[];
  onToggleType: (type: ActivityType) => void;
  selectedSession: string | null;
  onSessionChange: (sessionId: string | null) => void;
  errorsOnly: boolean;
  onErrorsOnlyChange: (value: boolean) => void;
  isLive: boolean;
  onLiveChange: (value: boolean) => void;
}

function FeedToolbar({
  selectedTypes,
  onToggleType,
  selectedSession,
  onSessionChange,
  errorsOnly,
  onErrorsOnlyChange,
  isLive,
  onLiveChange,
}: FeedToolbarProps) {
  const activityTypeFilters: { type: ActivityType; label: string; color: string }[] = [
    { type: 'run_started', label: 'Started', color: 'blue' },
    { type: 'run_completed', label: 'Completed', color: 'emerald' },
    { type: 'run_failed', label: 'Failed', color: 'red' },
    { type: 'run_stopped', label: 'Stopped', color: 'gray' },
    { type: 'session_event', label: 'Events', color: 'purple' },
  ];

  return (
    <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Filter:</span>
          {activityTypeFilters.map(({ type, label, color }) => {
            const isSelected = selectedTypes.length === 0 || selectedTypes.includes(type);
            return (
              <button
                key={type}
                onClick={() => onToggleType(type)}
                className={`px-2.5 py-1 text-xs font-medium rounded-full transition-all ${
                  isSelected
                    ? `bg-${color}-100 text-${color}-700 ring-1 ring-${color}-300`
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedSession || ''}
            onChange={(e) => onSessionChange(e.target.value || null)}
            className="text-sm border border-gray-300 rounded-md px-2 py-1.5"
          >
            <option value="">All Sessions</option>
            {mockSessions.map((s) => (
              <option key={s.session_id} value={s.session_id}>
                {s.name}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={errorsOnly}
              onChange={(e) => onErrorsOnlyChange(e.target.checked)}
              className="rounded border-gray-300"
            />
            Errors only
          </label>

          <button
            onClick={() => onLiveChange(!isLive)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium rounded-md transition-all ${
              isLive
                ? 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-300'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {isLive && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative rounded-full h-2 w-2 bg-emerald-500" />
              </span>
            )}
            {isLive ? 'Live' : 'Paused'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ActivityFeedTab() {
  const [selectedTypes, setSelectedTypes] = useState<ActivityType[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [isLive, setIsLive] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [visibleCount, setVisibleCount] = useState(20);

  const handleToggleType = (type: ActivityType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Filter activities
  const filteredActivities = mockActivities.filter((activity) => {
    // Type filter
    if (selectedTypes.length > 0 && !selectedTypes.includes(activity.type)) {
      return false;
    }

    // Session filter
    if (selectedSession && activity.sessionId !== selectedSession) {
      return false;
    }

    // Errors only filter
    if (errorsOnly) {
      if (activity.type === 'run_failed') return true;
      if (
        activity.type === 'session_event' &&
        (activity as EventActivityItem).eventType.includes('error')
      ) {
        return true;
      }
      return false;
    }

    return true;
  });

  const visibleActivities = filteredActivities.slice(0, visibleCount);
  const hasMore = visibleCount < filteredActivities.length;

  const loadMore = () => {
    setVisibleCount((prev) => prev + 20);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-gray-50">
      <FeedToolbar
        selectedTypes={selectedTypes}
        onToggleType={handleToggleType}
        selectedSession={selectedSession}
        onSessionChange={setSelectedSession}
        errorsOnly={errorsOnly}
        onErrorsOnlyChange={setErrorsOnly}
        isLive={isLive}
        onLiveChange={setIsLive}
      />

      <div className="flex-1 overflow-y-auto px-4 py-4">
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

          {visibleActivities.length === 0 ? (
            <div className="text-center py-12">
              <Activity className="w-16 h-16 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No activity found</h3>
              <p className="text-sm text-gray-500 mt-1">
                {errorsOnly
                  ? 'No errors to display with the current filters'
                  : 'Try adjusting your filters to see more activity'}
              </p>
            </div>
          ) : (
            <>
              {visibleActivities.map((activity, index) => (
                <ActivityCard
                  key={activity.id}
                  activity={activity}
                  expanded={expandedIds.has(activity.id)}
                  onToggle={() => toggleExpanded(activity.id)}
                  animate={isLive && index === 0}
                />
              ))}

              {hasMore && (
                <div className="flex items-center justify-center py-4">
                  <button
                    onClick={loadMore}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:bg-white rounded-lg border border-gray-200 transition-colors"
                  >
                    <Loader2 className="w-4 h-4" />
                    Load more ({filteredActivities.length - visibleCount} remaining)
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 bg-white border-t border-gray-200 px-4 py-2 flex items-center justify-between text-sm text-gray-500">
        <span>
          Showing {visibleActivities.length} of {filteredActivities.length} activities
        </span>
        {isLive && (
          <span className="flex items-center gap-1.5 text-emerald-600">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            Live
          </span>
        )}
      </div>
    </div>
  );
}
