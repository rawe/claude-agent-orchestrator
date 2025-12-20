import { useState, useEffect, useCallback } from 'react';
import { runService } from '@/services';
import type { Run, RunStatus } from '@/types';
import { RunsTable, RunDetailPanel } from '@/components/features/runs';
import { RefreshCw, Zap, Filter } from 'lucide-react';

const STATUS_OPTIONS: { value: RunStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'claimed', label: 'Claimed' },
  { value: 'running', label: 'Running' },
  { value: 'stopping', label: 'Stopping' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'stopped', label: 'Stopped' },
];

export function Runs() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RunStatus | 'all'>('all');
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runService.getRuns();
      setRuns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runs');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchRuns]);

  const handleSelectRun = (run: Run) => {
    setSelectedRun(run);
  };

  const handleCloseDetail = () => {
    setSelectedRun(null);
  };

  // Calculate status counts
  const statusCounts = runs.reduce(
    (acc, run) => {
      acc[run.status] = (acc[run.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const getStatusSummary = () => {
    const parts = [];
    if (statusCounts.running) parts.push(`${statusCounts.running} running`);
    if (statusCounts.pending) parts.push(`${statusCounts.pending} pending`);
    if (statusCounts.completed) parts.push(`${statusCounts.completed} completed`);
    if (statusCounts.failed) parts.push(`${statusCounts.failed} failed`);
    return parts.length > 0 ? parts.join(', ') : 'No runs';
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 bg-white border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Agent Runs</h2>
          <p className="text-sm text-gray-500">{getStatusSummary()}</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as RunStatus | 'all')}
              className="text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                  {option.value !== 'all' && statusCounts[option.value]
                    ? ` (${statusCounts[option.value]})`
                    : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Auto-refresh Toggle */}
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <div className="relative">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600"></div>
            </div>
            <span>Auto-refresh</span>
          </label>

          {/* Refresh Button */}
          <button
            onClick={fetchRuns}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {error && (
          <div className="m-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {loading && runs.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            Loading runs...
          </div>
        ) : runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-500">
            <Zap className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-sm font-medium">No runs found</p>
            <p className="text-xs text-gray-400 mt-1">Runs will appear here when agents are executed</p>
          </div>
        ) : (
          <RunsTable
            runs={runs}
            loading={loading}
            onSelectRun={handleSelectRun}
            statusFilter={statusFilter}
          />
        )}
      </div>

      {/* Detail Panel */}
      <RunDetailPanel
        run={selectedRun}
        isOpen={selectedRun !== null}
        onClose={handleCloseDetail}
      />
    </div>
  );
}
