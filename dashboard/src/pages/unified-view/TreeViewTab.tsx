import { useState } from 'react';
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
} from 'lucide-react';
import { MockSession, MockRun } from './types';
import { mockSessions, mockRuns } from './mock-data';
import { formatRelativeTime, formatDuration, getEventTypeStyles } from './utils';

// ============================================================================
// APPROACH 3: TREE VIEW TAB
// ============================================================================

interface TreeNodeData {
  session: MockSession;
  runs: MockRun[];
  children: TreeNodeData[];
}

function buildTree(sessions: MockSession[], runs: MockRun[]): TreeNodeData[] {
  const rootSessions = sessions.filter((s) => !s.parent_session_id);

  function buildNode(session: MockSession): TreeNodeData {
    const sessionRuns = runs
      .filter((r) => r.session_id === session.session_id)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
    const childSessions = sessions.filter((s) => s.parent_session_id === session.session_id);

    return {
      session,
      runs: sessionRuns,
      children: childSessions.map(buildNode),
    };
  }

  return rootSessions.map(buildNode);
}

interface SessionTreeNodeProps {
  node: TreeNodeData;
  depth: number;
  expandState: Record<string, boolean>;
  onToggle: (sessionId: string) => void;
  selectedId: string | null;
  onSelect: (type: 'session' | 'run', id: string) => void;
}

function SessionTreeNode({
  node,
  depth,
  expandState,
  onToggle,
  selectedId,
  onSelect,
}: SessionTreeNodeProps) {
  const { session, runs, children } = node;
  const isExpanded = expandState[session.session_id] ?? true;
  const isSelected = selectedId === session.session_id;
  const hasActiveRun = runs.some((r) => ['running', 'pending', 'claimed'].includes(r.status));

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
        onClick={() => onSelect('session', session.session_id)}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle(session.session_id);
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
            <span className="font-medium text-gray-900 truncate">{session.name}</span>
            <StatusBadge status={session.status} />
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Bot className="w-3 h-3" />
              {session.agent_name}
            </span>
            <span>{runs.length} runs</span>
            {children.length > 0 && <span>{children.length} children</span>}
          </div>

          <div className="mt-1 text-xs text-gray-400">{formatRelativeTime(session.created_at)}</div>
        </div>
      </div>

      {/* Expanded content: runs and children */}
      {isExpanded && (
        <div className="space-y-1">
          {/* Runs */}
          {runs.map((run, index) => (
            <RunTreeNode
              key={run.run_id}
              run={run}
              runNumber={index + 1}
              depth={depth + 1}
              isSelected={selectedId === run.run_id}
              onSelect={() => onSelect('run', run.run_id)}
            />
          ))}

          {/* Child sessions */}
          {children.map((childNode) => (
            <SessionTreeNode
              key={childNode.session.session_id}
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
  run: MockRun;
  runNumber: number;
  depth: number;
  isSelected: boolean;
  onSelect: () => void;
}

function RunTreeNode({ run, runNumber, depth, isSelected, onSelect }: RunTreeNodeProps) {
  const isActive = ['pending', 'claimed', 'running', 'stopping'].includes(run.status);
  const TypeIcon = run.type === 'start_session' ? Play : RotateCcw;

  const getDuration = () => {
    if (!run.started_at) return '-';
    const start = new Date(run.started_at).getTime();
    const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now();
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
        <span className="text-sm font-medium text-gray-700">Run #{runNumber}</span>
        <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
          <TypeIcon className="w-3 h-3 mr-1" />
          {run.type === 'start_session' ? 'start' : 'resume'}
        </Badge>
        <RunStatusBadge status={run.status} />
        <span className="text-xs text-gray-500">{getDuration()}</span>
      </div>

      <span className="text-xs text-gray-400 font-mono">{run.run_id.slice(0, 8)}</span>
    </div>
  );
}

interface TreeDetailPanelProps {
  type: 'session' | 'run';
  session: MockSession | null;
  run: MockRun | null;
  onClose: () => void;
}

function TreeDetailPanel({ type, session, run, onClose }: TreeDetailPanelProps) {
  if (type === 'session' && session) {
    const sessionRuns = mockRuns.filter((r) => r.session_id === session.session_id);
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
              <h4 className="text-lg font-medium text-gray-900">{session.name}</h4>
              <StatusBadge status={session.status} />
            </div>
            <div className="text-xs text-gray-500 font-mono mb-3">{session.session_id}</div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Agent:</span>
                <span className="ml-2 text-gray-900">{session.agent_name}</span>
              </div>
              <div>
                <span className="text-gray-500">Runs:</span>
                <span className="ml-2 text-gray-900">{sessionRuns.length}</span>
              </div>
              <div>
                <span className="text-gray-500">Created:</span>
                <span className="ml-2 text-gray-900">{formatRelativeTime(session.created_at)}</span>
              </div>
              {session.parent_session_id && (
                <div>
                  <span className="text-gray-500">Parent:</span>
                  <span className="ml-2 text-gray-900 font-mono text-xs">{session.parent_session_id.slice(0, 12)}...</span>
                </div>
              )}
            </div>
          </div>

          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Runs ({sessionRuns.length})</h5>
            <div className="space-y-2">
              {sessionRuns.map((r, i) => (
                <div key={r.run_id} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                  <span className="text-sm font-medium">#{i + 1}</span>
                  <Badge variant={r.type === 'start_session' ? 'info' : 'default'} size="sm">
                    {r.type === 'start_session' ? 'start' : 'resume'}
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
            <div className="text-xs text-gray-500 font-mono mb-3">{run.run_id}</div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant={run.type === 'start_session' ? 'info' : 'default'} size="sm">
                  {run.type === 'start_session' ? 'start' : 'resume'}
                </Badge>
                <span className="text-gray-500">•</span>
                <span className="text-gray-900">{run.agent_name}</span>
              </div>
              <div>
                <span className="text-gray-500">Created:</span>
                <span className="ml-2 text-gray-900">{formatRelativeTime(run.created_at)}</span>
              </div>
            </div>
          </div>

          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Prompt</h5>
            <div className="p-2 bg-gray-50 rounded text-sm text-gray-700">{run.prompt}</div>
          </div>

          <div>
            <h5 className="text-sm font-medium text-gray-700 mb-2">Events ({run.events.length})</h5>
            <div className="space-y-2 pl-3 border-l-2 border-gray-200">
              {run.events.map((event, index) => (
                <div key={index} className="py-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-xs px-1.5 py-0.5 rounded border ${getEventTypeStyles(event.type)}`}>
                      {event.type}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">{event.timestamp}</span>
                  </div>
                  <p className="text-sm text-gray-600">{event.summary}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export function TreeViewTab() {
  const [expandState, setExpandState] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    mockSessions.forEach((s) => {
      initial[s.session_id] = !s.parent_session_id; // Expand root sessions by default
    });
    return initial;
  });

  const [selectedItem, setSelectedItem] = useState<{ type: 'session' | 'run'; id: string } | null>(null);

  const tree = buildTree(mockSessions, mockRuns);

  const toggleNode = (sessionId: string) => {
    setExpandState((prev) => ({ ...prev, [sessionId]: !prev[sessionId] }));
  };

  const expandAll = () => {
    const newState: Record<string, boolean> = {};
    mockSessions.forEach((s) => {
      newState[s.session_id] = true;
    });
    setExpandState(newState);
  };

  const collapseAll = () => {
    const newState: Record<string, boolean> = {};
    mockSessions.forEach((s) => {
      newState[s.session_id] = false;
    });
    setExpandState(newState);
  };

  const handleSelect = (type: 'session' | 'run', id: string) => {
    setSelectedItem({ type, id });
  };

  const selectedSession = selectedItem?.type === 'session' ? mockSessions.find((s) => s.session_id === selectedItem.id) || null : null;
  const selectedRun = selectedItem?.type === 'run' ? mockRuns.find((r) => r.run_id === selectedItem.id) || null : null;

  const totalRuns = mockRuns.length;
  const activeSessions = mockSessions.filter((s) => s.status === 'running').length;
  const activeRuns = mockRuns.filter((r) => ['running', 'pending', 'claimed'].includes(r.status)).length;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>{mockSessions.length} sessions</span>
          <span>•</span>
          <span>{totalRuns} runs</span>
          {activeSessions > 0 && (
            <>
              <span>•</span>
              <span className="text-emerald-600">{activeSessions} active sessions</span>
            </>
          )}
          {activeRuns > 0 && (
            <>
              <span>•</span>
              <span className="text-blue-600">{activeRuns} running</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
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
            {tree.map((node) => (
              <SessionTreeNode
                key={node.session.session_id}
                node={node}
                depth={0}
                expandState={expandState}
                onToggle={toggleNode}
                selectedId={selectedItem?.id || null}
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
            onClose={() => setSelectedItem(null)}
          />
        )}
      </div>
    </div>
  );
}
