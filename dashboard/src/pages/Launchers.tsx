import { useState, useEffect, useCallback } from 'react';
import { launcherService } from '@/services';
import { Launcher } from '@/types';
import { formatRelativeTime, formatAbsoluteTime, getLastPathSegment } from '@/utils/formatters';
import { RefreshCw, Server, Folder, Clock, Activity } from 'lucide-react';

function LauncherCard({ launcher }: { launcher: Launcher }) {
  const projectFolder = launcher.project_dir ? getLastPathSegment(launcher.project_dir) : null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-sm transition-shadow">
      {/* Status bar */}
      <div className={`h-1 ${launcher.is_alive ? 'bg-emerald-500' : 'bg-gray-300'}`} />

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
            className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${
              launcher.is_alive
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            <Activity className="w-3 h-3" />
            {launcher.is_alive ? 'Online' : 'Offline'}
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
            className="text-xs text-gray-400 pl-5"
            title={formatAbsoluteTime(launcher.last_heartbeat)}
          >
            Last heartbeat {formatRelativeTime(launcher.last_heartbeat)}
          </div>
        </div>
      </div>
    </div>
  );
}

export function Launchers() {
  const [launchers, setLaunchers] = useState<Launcher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLaunchers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await launcherService.getLaunchers();
      setLaunchers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch launchers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLaunchers();
  }, [fetchLaunchers]);

  const onlineCount = launchers.filter((l) => l.is_alive).length;
  const offlineCount = launchers.length - onlineCount;

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Agent Launchers</h2>
          <p className="text-sm text-gray-500">
            {launchers.length === 0
              ? 'No launchers registered'
              : `${onlineCount} online, ${offlineCount} offline`}
          </p>
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
            <p className="text-xs text-gray-400 mt-1">
              Start an agent launcher to see it here
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {launchers.map((launcher) => (
              <LauncherCard key={launcher.launcher_id} launcher={launcher} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
