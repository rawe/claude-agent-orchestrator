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

interface SessionCardWithRunsProps {
  session: MockSession;
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
          <span className="text-sm font-medium text-gray-900 truncate">{session.name}</span>
        </div>
        <StatusBadge status={session.status} />
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
        <span className="flex items-center gap-1">
          <Hash className="w-3 h-3" />
          {session.agent_name}
        </span>
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {formatRelativeTime(session.created_at)}
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
  run: MockRun;
  defaultExpanded?: boolean;
}

function RunBlock({ run, defaultExpanded = false }: RunBlockProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [eventsExpanded, setEventsExpanded] = useState(true);
  const [showPrompt, setShowPrompt] = useState(false);

  const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);
  const RunTypeIcon = run.type === 'start_session' ? Play : RotateCcw;

  const getRunDuration = () => {
    if (!run.started_at) return '-';
    const start = new Date(run.started_at).getTime();
    const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now();
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
            run.type === 'start_session' ? 'bg-blue-100' : 'bg-amber-100'
          }`}
        >
          <RunTypeIcon
            className={`w-4 h-4 ${run.type === 'start_session' ? 'text-blue-600' : 'text-amber-600'}`}
          />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">Run #{run.runNumber}</span>
            <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
              {run.type === 'start_session' ? 'start' : 'resume'}
            </Badge>
            <RunStatusBadge status={run.status} />
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {getRunDuration()}
            </span>
            {run.runner_id && (
              <span className="flex items-center gap-1">
                <Server className="w-3 h-3" />
                {run.runner_id.slice(0, 12)}...
              </span>
            )}
            <span>{formatRelativeTime(run.created_at)}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <MessageSquare className="w-3.5 h-3.5" />
          {run.events.length} events
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
              <span className="font-medium">Prompt</span>
            </button>
            {showPrompt && (
              <div className="mt-2 p-3 bg-white rounded border border-gray-200">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                  {run.prompt}
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
              <div className="space-y-2 pl-4 border-l-2 border-gray-200">
                {run.events.map((event, index) => (
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
            )}
          </div>

          <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
            <span className="font-mono">{run.run_id}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function SessionTimelineTab() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(mockSessions[0].session_id);
  const [sidebarVisible, setSidebarVisible] = useState(true);

  const selectedSession = mockSessions.find((s) => s.session_id === selectedSessionId);
  const sessionRuns = mockRuns.filter((r) => r.session_id === selectedSessionId);

  return (
    <div className="flex-1 flex min-h-0">
      {sidebarVisible && (
        <div className="w-80 border-r border-gray-200 bg-white flex-shrink-0 flex flex-col">
          <div className="p-3 border-b border-gray-200">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Sessions ({mockSessions.length})
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {mockSessions.map((session) => (
              <SessionCardWithRuns
                key={session.session_id}
                session={session}
                isSelected={selectedSessionId === session.session_id}
                onSelect={() => setSelectedSessionId(session.session_id)}
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
                  <h2 className="text-base font-semibold text-gray-900">{selectedSession.name}</h2>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>Agent: {selectedSession.agent_name}</span>
                    <span>-</span>
                    <span>Created {formatRelativeTime(selectedSession.created_at)}</span>
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
              {sessionRuns.map((run, index) => (
                <RunBlock key={run.run_id} run={run} defaultExpanded={index === 0} />
              ))}
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
