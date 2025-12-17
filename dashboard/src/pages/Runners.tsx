import { useState, useEffect, useCallback } from 'react';
import { runnerService } from '@/services';
import { Runner, RunnerStatus } from '@/types';
import { ConfirmModal } from '@/components/common';
import { formatRelativeTime, formatAbsoluteTime, getLastPathSegment } from '@/utils/formatters';
import { RefreshCw, Server, Folder, Clock, Activity, Power, AlertTriangle, Terminal } from 'lucide-react';

interface RunnerCardProps {
  runner: Runner;
  isDeregistering: boolean;
  onDeregister: (runner: Runner) => void;
}

function getStatusConfig(status: RunnerStatus, isDeregistering: boolean) {
  if (isDeregistering) {
    return {
      barColor: 'bg-amber-400',
      badgeBg: 'bg-amber-100',
      badgeText: 'text-amber-700',
      icon: Power,
      label: 'Shutting down...',
      cardOpacity: 'opacity-60',
    };
  }

  switch (status) {
    case 'online':
      return {
        barColor: 'bg-emerald-500',
        badgeBg: 'bg-emerald-100',
        badgeText: 'text-emerald-700',
        icon: Activity,
        label: 'Online',
        cardOpacity: '',
      };
    case 'stale':
      return {
        barColor: 'bg-amber-500',
        badgeBg: 'bg-amber-100',
        badgeText: 'text-amber-700',
        icon: AlertTriangle,
        label: 'Stale',
        cardOpacity: 'opacity-75',
      };
    default:
      return {
        barColor: 'bg-gray-300',
        badgeBg: 'bg-gray-100',
        badgeText: 'text-gray-600',
        icon: Activity,
        label: 'Offline',
        cardOpacity: 'opacity-50',
      };
  }
}

function RunnerCard({ runner, isDeregistering, onDeregister }: RunnerCardProps) {
  const projectFolder = runner.project_dir ? getLastPathSegment(runner.project_dir) : null;
  const config = getStatusConfig(runner.status, isDeregistering);
  const StatusIcon = config.icon;

  return (
    <div
      className={`group bg-white rounded-lg border border-gray-200 overflow-hidden transition-all duration-300 ${
        isDeregistering ? 'animate-pulse' : 'hover:shadow-sm'
      } ${config.cardOpacity}`}
    >
      {/* Status bar */}
      <div className={`h-1 ${config.barColor} transition-colors duration-300`} />

      <div className="p-4">
        {/* Header: Hostname and Status */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <Server className="w-5 h-5 text-gray-400 flex-shrink-0" />
            <h3 className="text-sm font-semibold text-gray-900 truncate">
              {runner.hostname || 'Unknown Host'}
            </h3>
          </div>
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${config.badgeBg} ${config.badgeText}`}
          >
            <StatusIcon className="w-3 h-3" />
            {config.label}
          </span>
        </div>

        {/* Runner ID */}
        <div className="mb-3">
          <span className="text-xs text-gray-400 font-mono">{runner.runner_id}</span>
        </div>

        {/* Project Directory */}
        {projectFolder && (
          <div className="flex items-center gap-1.5 text-xs text-gray-600 mb-2">
            <Folder className="w-3.5 h-3.5 text-gray-400" />
            <span className="truncate" title={runner.project_dir || undefined}>
              {projectFolder}
            </span>
          </div>
        )}

        {/* Executor Type */}
        {runner.executor_type && (
          <div className="flex items-center gap-1.5 text-xs text-gray-600 mb-2">
            <Terminal className="w-3.5 h-3.5 text-gray-400" />
            <span className="truncate">{runner.executor_type}</span>
          </div>
        )}

        {/* Timestamps */}
        <div className="space-y-1 pt-2 border-t border-gray-100">
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Clock className="w-3.5 h-3.5 text-gray-400" />
            <span>Registered {formatRelativeTime(runner.registered_at)}</span>
          </div>
          <div
            className={`text-xs pl-5 ${runner.status === 'stale' ? 'text-amber-600 font-medium' : 'text-gray-400'}`}
            title={formatAbsoluteTime(runner.last_heartbeat)}
          >
            Last heartbeat {formatRelativeTime(runner.last_heartbeat)}
            {runner.status === 'stale' && ' (no connection)'}
          </div>
        </div>

        {/* Deregister button - visible on hover, disabled while deregistering */}
        <div
          className={`mt-3 pt-2 border-t border-gray-100 transition-opacity ${
            isDeregistering ? 'opacity-50' : 'opacity-0 group-hover:opacity-100'
          }`}
        >
          <button
            onClick={() => onDeregister(runner)}
            disabled={isDeregistering}
            className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 rounded transition-colors disabled:cursor-not-allowed disabled:hover:bg-transparent"
          >
            <Power className="w-3.5 h-3.5" />
            {isDeregistering ? 'Deregistering...' : 'Deregister'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function Runners() {
  const [runners, setRunners] = useState<Runner[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deregisteringIds, setDeregisteringIds] = useState<Set<string>>(new Set());
  const [deregisterConfirm, setDeregisterConfirm] = useState<{
    isOpen: boolean;
    runner: Runner | null;
  }>({ isOpen: false, runner: null });

  const fetchRunners = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runnerService.getRunners();
      setRunners(data);
      // Clear deregistering state for runners that are no longer in the list
      setDeregisteringIds((prev) => {
        const currentIds = new Set(data.map((r) => r.runner_id));
        const newSet = new Set<string>();
        prev.forEach((id) => {
          if (currentIds.has(id)) {
            newSet.add(id);
          }
        });
        return newSet;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runners');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRunners();
  }, [fetchRunners]);

  const handleDeregisterClick = (runner: Runner) => {
    setDeregisterConfirm({ isOpen: true, runner });
  };

  const handleDeregisterConfirm = async () => {
    if (!deregisterConfirm.runner) return;

    const runnerId = deregisterConfirm.runner.runner_id;

    // Close modal immediately and mark as deregistering
    setDeregisterConfirm({ isOpen: false, runner: null });
    setDeregisteringIds((prev) => new Set(prev).add(runnerId));

    try {
      await runnerService.deregisterRunner(runnerId);
      // Don't reload immediately - let the visual feedback show
      // The user can manually refresh or we'll clean up on next refresh
    } catch (err) {
      // Remove from deregistering set on error
      setDeregisteringIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(runnerId);
        return newSet;
      });
      setError(err instanceof Error ? err.message : 'Failed to deregister runner');
    }
  };

  const onlineCount = runners.filter((r) => r.status === 'online' && !deregisteringIds.has(r.runner_id)).length;
  const staleCount = runners.filter((r) => r.status === 'stale').length;
  const deregisteringCount = deregisteringIds.size;

  const getStatusSummary = () => {
    const parts = [];
    if (onlineCount > 0) parts.push(`${onlineCount} online`);
    if (staleCount > 0) parts.push(`${staleCount} stale`);
    if (deregisteringCount > 0) parts.push(`${deregisteringCount} shutting down`);
    return parts.length > 0 ? parts.join(', ') : 'No runners registered';
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Agent Runners</h2>
          <p className="text-sm text-gray-500">{getStatusSummary()}</p>
        </div>
        <button
          onClick={fetchRunners}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && runners.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            Loading runners...
          </div>
        ) : runners.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-500">
            <Server className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-sm font-medium">No runners registered</p>
            <p className="text-xs text-gray-400 mt-1">Start an agent runner to see it here</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {runners.map((runner) => (
              <RunnerCard
                key={runner.runner_id}
                runner={runner}
                isDeregistering={deregisteringIds.has(runner.runner_id)}
                onDeregister={handleDeregisterClick}
              />
            ))}
          </div>
        )}
      </div>

      {/* Deregister Confirmation Modal */}
      <ConfirmModal
        isOpen={deregisterConfirm.isOpen}
        onClose={() => setDeregisterConfirm({ isOpen: false, runner: null })}
        onConfirm={handleDeregisterConfirm}
        title="Deregister Runner"
        message={`Are you sure you want to deregister "${deregisterConfirm.runner?.hostname || deregisterConfirm.runner?.runner_id}"? The runner will be signaled to shut down.`}
        confirmText="Deregister"
        variant="danger"
      />
    </div>
  );
}
