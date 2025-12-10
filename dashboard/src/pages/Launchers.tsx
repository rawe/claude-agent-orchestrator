import { useState, useEffect, useCallback } from 'react';
import { launcherService } from '@/services';
import { Launcher, LauncherStatus } from '@/types';
import { ConfirmModal } from '@/components/common';
import { formatRelativeTime, formatAbsoluteTime, getLastPathSegment } from '@/utils/formatters';
import { RefreshCw, Server, Folder, Clock, Activity, Power, AlertTriangle } from 'lucide-react';

interface LauncherCardProps {
  launcher: Launcher;
  isDeregistering: boolean;
  onDeregister: (launcher: Launcher) => void;
}

function getStatusConfig(status: LauncherStatus, isDeregistering: boolean) {
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

function LauncherCard({ launcher, isDeregistering, onDeregister }: LauncherCardProps) {
  const projectFolder = launcher.project_dir ? getLastPathSegment(launcher.project_dir) : null;
  const config = getStatusConfig(launcher.status, isDeregistering);
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
              {launcher.hostname || 'Unknown Host'}
            </h3>
          </div>
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${config.badgeBg} ${config.badgeText}`}
          >
            <StatusIcon className="w-3 h-3" />
            {config.label}
          </span>
        </div>

        {/* Launcher ID */}
        <div className="mb-3">
          <span className="text-xs text-gray-400 font-mono">{launcher.launcher_id}</span>
        </div>

        {/* Project Directory */}
        {projectFolder && (
          <div className="flex items-center gap-1.5 text-xs text-gray-600 mb-2">
            <Folder className="w-3.5 h-3.5 text-gray-400" />
            <span className="truncate" title={launcher.project_dir || undefined}>
              {projectFolder}
            </span>
          </div>
        )}

        {/* Timestamps */}
        <div className="space-y-1 pt-2 border-t border-gray-100">
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Clock className="w-3.5 h-3.5 text-gray-400" />
            <span>Registered {formatRelativeTime(launcher.registered_at)}</span>
          </div>
          <div
            className={`text-xs pl-5 ${launcher.status === 'stale' ? 'text-amber-600 font-medium' : 'text-gray-400'}`}
            title={formatAbsoluteTime(launcher.last_heartbeat)}
          >
            Last heartbeat {formatRelativeTime(launcher.last_heartbeat)}
            {launcher.status === 'stale' && ' (no connection)'}
          </div>
        </div>

        {/* Deregister button - visible on hover, disabled while deregistering */}
        <div
          className={`mt-3 pt-2 border-t border-gray-100 transition-opacity ${
            isDeregistering ? 'opacity-50' : 'opacity-0 group-hover:opacity-100'
          }`}
        >
          <button
            onClick={() => onDeregister(launcher)}
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

export function Launchers() {
  const [launchers, setLaunchers] = useState<Launcher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deregisteringIds, setDeregisteringIds] = useState<Set<string>>(new Set());
  const [deregisterConfirm, setDeregisterConfirm] = useState<{
    isOpen: boolean;
    launcher: Launcher | null;
  }>({ isOpen: false, launcher: null });

  const fetchLaunchers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await launcherService.getLaunchers();
      setLaunchers(data);
      // Clear deregistering state for launchers that are no longer in the list
      setDeregisteringIds((prev) => {
        const currentIds = new Set(data.map((l) => l.launcher_id));
        const newSet = new Set<string>();
        prev.forEach((id) => {
          if (currentIds.has(id)) {
            newSet.add(id);
          }
        });
        return newSet;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch launchers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLaunchers();
  }, [fetchLaunchers]);

  const handleDeregisterClick = (launcher: Launcher) => {
    setDeregisterConfirm({ isOpen: true, launcher });
  };

  const handleDeregisterConfirm = async () => {
    if (!deregisterConfirm.launcher) return;

    const launcherId = deregisterConfirm.launcher.launcher_id;

    // Close modal immediately and mark as deregistering
    setDeregisterConfirm({ isOpen: false, launcher: null });
    setDeregisteringIds((prev) => new Set(prev).add(launcherId));

    try {
      await launcherService.deregisterLauncher(launcherId);
      // Don't reload immediately - let the visual feedback show
      // The user can manually refresh or we'll clean up on next refresh
    } catch (err) {
      // Remove from deregistering set on error
      setDeregisteringIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(launcherId);
        return newSet;
      });
      setError(err instanceof Error ? err.message : 'Failed to deregister launcher');
    }
  };

  const onlineCount = launchers.filter((l) => l.status === 'online' && !deregisteringIds.has(l.launcher_id)).length;
  const staleCount = launchers.filter((l) => l.status === 'stale').length;
  const deregisteringCount = deregisteringIds.size;

  const getStatusSummary = () => {
    const parts = [];
    if (onlineCount > 0) parts.push(`${onlineCount} online`);
    if (staleCount > 0) parts.push(`${staleCount} stale`);
    if (deregisteringCount > 0) parts.push(`${deregisteringCount} shutting down`);
    return parts.length > 0 ? parts.join(', ') : 'No launchers registered';
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Agent Launchers</h2>
          <p className="text-sm text-gray-500">{getStatusSummary()}</p>
        </div>
        <button
          onClick={fetchLaunchers}
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

        {loading && launchers.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            Loading launchers...
          </div>
        ) : launchers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-500">
            <Server className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-sm font-medium">No launchers registered</p>
            <p className="text-xs text-gray-400 mt-1">Start an agent launcher to see it here</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {launchers.map((launcher) => (
              <LauncherCard
                key={launcher.launcher_id}
                launcher={launcher}
                isDeregistering={deregisteringIds.has(launcher.launcher_id)}
                onDeregister={handleDeregisterClick}
              />
            ))}
          </div>
        )}
      </div>

      {/* Deregister Confirmation Modal */}
      <ConfirmModal
        isOpen={deregisterConfirm.isOpen}
        onClose={() => setDeregisterConfirm({ isOpen: false, launcher: null })}
        onConfirm={handleDeregisterConfirm}
        title="Deregister Launcher"
        message={`Are you sure you want to deregister "${deregisterConfirm.launcher?.hostname || deregisterConfirm.launcher?.launcher_id}"? The launcher will be signaled to shut down.`}
        confirmText="Deregister"
        variant="danger"
      />
    </div>
  );
}
