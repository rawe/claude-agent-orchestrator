import { useState } from 'react';
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
} from 'lucide-react';
import {
  MockRun,
  mockSessions,
  mockRuns,
  formatRelativeTime,
  formatDuration,
  getEventTypeStyles,
} from './';

interface RunListItemProps {
  run: MockRun;
  isSelected: boolean;
  onSelect: () => void;
}

function RunListItem({ run, isSelected, onSelect }: RunListItemProps) {
  const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);

  const getRunDuration = () => {
    if (!run.started_at) return 'queued';
    const start = new Date(run.started_at).getTime();
    const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now();
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
        <span className="font-mono text-xs text-gray-500">{run.run_id.slice(0, 8)}</span>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-medium text-gray-900 truncate">{run.agent_name}</span>
        <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
          {run.type === 'start_session' ? 'start' : 'resume'}
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
        <span>{formatRelativeTime(run.created_at)}</span>
      </div>
    </button>
  );
}

interface RunHistoryChipProps {
  run: MockRun;
  index: number;
  isSelected: boolean;
  onClick: () => void;
}

function RunHistoryChip({ run, index, isSelected, onClick }: RunHistoryChipProps) {
  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700',
    claimed: 'bg-blue-100 text-blue-700',
    running: 'bg-emerald-100 text-emerald-700',
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
      <span className="text-[10px] opacity-75">{run.type === 'start_session' ? 'start' : 'resume'}</span>
    </button>
  );
}

export function RunCentricTab() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(mockRuns[0].run_id);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  const selectedRun = mockRuns.find((r) => r.run_id === selectedRunId);
  const selectedSession = selectedRun
    ? mockSessions.find((s) => s.session_id === selectedRun.session_id)
    : null;
  const sessionRuns = selectedRun
    ? mockRuns.filter((r) => r.session_id === selectedRun.session_id)
    : [];

  const filteredRuns = mockRuns
    .filter((r) => statusFilter === 'all' || r.status === statusFilter)
    .filter(
      (r) =>
        !search ||
        r.run_id.toLowerCase().includes(search.toLowerCase()) ||
        r.agent_name.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

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
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {filteredRuns.map((run) => (
            <RunListItem
              key={run.run_id}
              run={run}
              isSelected={selectedRunId === run.run_id}
              onSelect={() => setSelectedRunId(run.run_id)}
            />
          ))}
        </div>

        <div className="px-3 py-2 border-t border-gray-200 text-xs text-gray-500">
          {filteredRuns.length} of {mockRuns.length} runs
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
                    <h3 className="text-base font-semibold text-gray-900">{selectedSession.name}</h3>
                    <StatusBadge status={selectedSession.status} />
                  </div>
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <span className="font-mono">{selectedSession.session_id.slice(0, 12)}...</span>
                    <ExternalLink className="w-3 h-3 ml-1 text-primary-600" />
                  </div>
                </div>
                <div className="text-right text-sm text-gray-500">
                  <div className="flex items-center gap-1.5 justify-end">
                    <Clock className="w-4 h-4" />
                    {formatRelativeTime(selectedSession.created_at)}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5 text-gray-600">
                  <Bot className="w-4 h-4 text-gray-400" />
                  {selectedSession.agent_name}
                </div>
                {selectedSession.project_dir && (
                  <div className="flex items-center gap-1.5 text-gray-500">
                    <Folder className="w-4 h-4 text-gray-400" />
                    <span className="truncate max-w-[180px]">{selectedSession.project_dir.split('/').pop()}</span>
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
                      key={run.run_id}
                      run={run}
                      index={index + 1}
                      isSelected={run.run_id === selectedRunId}
                      onClick={() => setSelectedRunId(run.run_id)}
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
                  <Badge variant={selectedRun.type === 'start_session' ? 'info' : 'default'} size="sm">
                    {selectedRun.type === 'start_session' ? 'start' : 'resume'}
                  </Badge>
                  <RunStatusBadge status={selectedRun.status} />
                </div>
                <span className="text-sm text-gray-500">{selectedRun.events.length} events</span>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                <div className="space-y-2 pl-4 border-l-2 border-gray-200">
                  {selectedRun.events.map((event, index) => (
                    <div key={index} className="flex items-start gap-3 py-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-gray-400 mt-2 -ml-[0.45rem]" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs px-2 py-0.5 rounded border ${getEventTypeStyles(event.type)}`}>
                            {event.type}
                          </span>
                          <span className="text-xs text-gray-400 font-mono">{event.timestamp}</span>
                        </div>
                        <p className="text-sm text-gray-700">{event.summary}</p>
                      </div>
                    </div>
                  ))}
                </div>
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
