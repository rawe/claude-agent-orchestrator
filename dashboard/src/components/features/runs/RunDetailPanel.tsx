import { Modal, CopyButton, Badge } from '@/components/common';
import { RunStatusBadge } from './RunStatusBadge';
import type { Run } from '@/types';
import {
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Folder,
  Server,
  User,
  Zap,
  AlertTriangle,
  ArrowDown,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface RunDetailPanelProps {
  run: Run | null;
  isOpen: boolean;
  onClose: () => void;
}

interface TimelineStep {
  label: string;
  timestamp: string | null;
  icon: React.ReactNode;
}

function formatElapsedTime(fromTime: string, toTime: string): string {
  const from = new Date(fromTime);
  const to = new Date(toTime);
  const diffMs = to.getTime() - from.getTime();

  if (diffMs < 0) return '-';
  if (diffMs < 1000) return `+${diffMs}ms`;
  if (diffMs < 60000) {
    const seconds = (diffMs / 1000).toFixed(1);
    return `+${seconds}s`;
  }
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.floor((diffMs % 60000) / 1000);
  if (minutes < 60) return `+${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `+${hours}h ${remainingMinutes}m`;
}

function formatDateTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function Timeline({ steps }: { steps: TimelineStep[] }) {
  return (
    <div className="space-y-0">
      {steps.map((step, index) => {
        const prevStep = index > 0 ? steps[index - 1] : null;
        const showElapsed = prevStep?.timestamp && step.timestamp;

        return (
          <div key={step.label}>
            {/* Elapsed time connector */}
            {index > 0 && (
              <div className="flex items-center gap-3 py-1">
                <div className="w-8 flex justify-center">
                  <ArrowDown className="w-3 h-3 text-gray-300" />
                </div>
                <span className="text-xs font-mono text-primary-600">
                  {showElapsed ? formatElapsedTime(prevStep.timestamp!, step.timestamp!) : '-'}
                </span>
              </div>
            )}

            {/* Step */}
            <div className="flex items-center gap-3">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full ${
                  step.timestamp ? 'bg-primary-100 text-primary-600' : 'bg-gray-100 text-gray-400'
                }`}
              >
                {step.icon}
              </div>
              <div className="flex-1 flex items-center justify-between">
                <span className={`text-sm font-medium ${step.timestamp ? 'text-gray-900' : 'text-gray-400'}`}>
                  {step.label}
                </span>
                <span className={`text-xs font-mono ${step.timestamp ? 'text-gray-600' : 'text-gray-400'}`}>
                  {step.timestamp ? formatDateTime(step.timestamp) : '-'}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function formatDuration(startTime: string | null, endTime: string | null): string {
  if (!startTime) return '-';
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const diffMs = end.getTime() - start.getTime();

  if (diffMs < 1000) return '<1 second';
  if (diffMs < 60000) return `${Math.floor(diffMs / 1000)} seconds`;
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.floor((diffMs % 60000) / 1000);
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function getModeLabel(mode: string): string {
  switch (mode) {
    case 'sync':
      return 'Synchronous';
    case 'async_poll':
      return 'Async (Polling)';
    case 'async_callback':
      return 'Async (Callback)';
    default:
      return mode;
  }
}

export function RunDetailPanel({ run, isOpen, onClose }: RunDetailPanelProps) {
  if (!run) return null;

  const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <Zap className="w-5 h-5 text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Run Details</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="font-mono text-xs text-gray-500">{run.run_id}</span>
              <CopyButton text={run.run_id} />
            </div>
          </div>
        </div>
        <RunStatusBadge status={run.status} />
      </div>

      <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Session ID</p>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-gray-900">{run.session_id}</span>
              <CopyButton text={run.session_id} />
              <Link
                to={`/sessions?id=${run.session_id}`}
                className="text-primary-600 hover:text-primary-700"
                title="View session"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Type</p>
            <Badge variant={run.type === 'start_session' ? 'info' : 'default'}>
              {run.type === 'start_session' ? 'Start Session' : 'Resume Session'}
            </Badge>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Agent</p>
            <div className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-sm text-gray-900">{run.agent_name || '-'}</span>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Execution Mode</p>
            <span className="text-sm text-gray-900">{getModeLabel(run.execution_mode)}</span>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Project Directory</p>
            <div className="flex items-center gap-1.5">
              <Folder className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-sm text-gray-900 truncate" title={run.project_dir || undefined}>
                {run.project_dir || '-'}
              </span>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Runner</p>
            <div className="flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-gray-400" />
              {run.runner_id ? (
                <>
                  <span className="font-mono text-sm text-gray-900 truncate" title={run.runner_id}>
                    {run.runner_id}
                  </span>
                  <CopyButton text={run.runner_id} />
                </>
              ) : (
                <span className="text-sm text-gray-400">Not assigned</span>
              )}
            </div>
          </div>

          {run.parent_session_id && (
            <div className="col-span-2">
              <p className="text-xs font-medium text-gray-500 uppercase mb-1">Parent Session</p>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm text-gray-900">{run.parent_session_id}</span>
                <CopyButton text={run.parent_session_id} />
              </div>
            </div>
          )}

          <div className="col-span-2">
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Duration</p>
            <span className={`text-sm ${isActive ? 'text-gray-900 font-medium' : 'text-gray-700'}`}>
              {formatDuration(run.started_at, run.completed_at)}
              {isActive && ' (in progress)'}
            </span>
          </div>
        </div>

        {/* Timeline */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Timeline</h4>
          <div className="bg-gray-50 rounded-lg p-4">
            <Timeline
              steps={[
                { label: 'Created', timestamp: run.created_at, icon: <Clock className="w-4 h-4" /> },
                { label: 'Claimed', timestamp: run.claimed_at, icon: <Zap className="w-4 h-4" /> },
                { label: 'Started', timestamp: run.started_at, icon: <Play className="w-4 h-4" /> },
                {
                  label: run.status === 'failed' ? 'Failed' : run.status === 'stopped' ? 'Stopped' : 'Completed',
                  timestamp: run.completed_at,
                  icon: run.status === 'failed' ? <XCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />,
                },
              ]}
            />
          </div>
        </div>

        {/* Prompt */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Prompt</h4>
          <div className="bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">{run.prompt}</pre>
          </div>
        </div>

        {/* Error */}
        {run.error && (
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              Error
            </h4>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-700">{run.error}</p>
            </div>
          </div>
        )}

        {/* Demands */}
        {run.demands && Object.keys(run.demands).some(k => run.demands![k as keyof typeof run.demands] !== null && run.demands![k as keyof typeof run.demands] !== undefined) && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Runner Demands</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                {JSON.stringify(run.demands, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex justify-end px-6 py-4 border-t border-gray-200 bg-gray-50">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
        >
          Close
        </button>
      </div>
    </Modal>
  );
}
