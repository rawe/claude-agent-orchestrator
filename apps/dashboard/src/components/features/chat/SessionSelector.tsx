import { useState, useMemo, useEffect, useRef } from 'react';
import { Session, SessionStatus } from '@/types';
import { StatusBadge } from '@/components/common';
import { formatRelativeTime, getLastPathSegment } from '@/utils/formatters';
import {
  Search,
  Filter,
  X,
  ChevronUp,
  Bot,
  Folder,
  MessageSquare,
  Lock,
} from 'lucide-react';

interface SessionSelectorProps {
  sessions: Session[];
  currentSessionId: string | null;
  isCurrentSessionActive: boolean;
  onSelectSession: (session: Session) => void;
  mode: 'new' | 'linked';
}

type SortOption = 'modified_desc' | 'modified_asc';

const statusOptions: { value: SessionStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'finished', label: 'Finished' },
  { value: 'stopped', label: 'Stopped' },
];

export function SessionSelector({
  sessions,
  currentSessionId,
  isCurrentSessionActive,
  onSelectSession,
  mode,
}: SessionSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>('all');
  const [sortBy] = useState<SortOption>('modified_desc');
  const panelRef = useRef<HTMLDivElement>(null);

  // Close panel when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Filter out running sessions (can't switch to them) and apply filters
  const filteredSessions = useMemo(() => {
    let filtered = sessions.filter((s) => s.status !== 'running');

    // Filter by search
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.session_id.toLowerCase().includes(searchLower) ||
          s.agent_name?.toLowerCase().includes(searchLower)
      );
    }

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter((s) => s.status === statusFilter);
    }

    // Sort
    filtered.sort((a, b) => {
      const aTime = new Date(a.modified_at || a.created_at).getTime();
      const bTime = new Date(b.modified_at || b.created_at).getTime();
      return sortBy === 'modified_desc' ? bTime - aTime : aTime - bTime;
    });

    return filtered;
  }, [sessions, search, statusFilter, sortBy]);

  // Get display info for the trigger button
  const currentSession = sessions.find((s) => s.session_id === currentSessionId);
  const triggerText = mode === 'new'
    ? 'New Chat'
    : currentSession?.session_id.slice(0, 16) || 'Select Session';

  const handleSelectSession = (session: Session) => {
    onSelectSession(session);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Trigger Button */}
      <button
        onClick={() => !isCurrentSessionActive && setIsOpen(!isOpen)}
        disabled={isCurrentSessionActive}
        className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-all w-full justify-between ${
          isCurrentSessionActive
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : isOpen
            ? 'bg-primary-100 text-primary-700 ring-2 ring-primary-500'
            : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
        }`}
        title={isCurrentSessionActive ? 'Cannot switch while chat is active' : 'Select session'}
      >
        <div className="flex items-center gap-2 min-w-0">
          {isCurrentSessionActive ? (
            <Lock className="w-4 h-4 flex-shrink-0" />
          ) : (
            <MessageSquare className="w-4 h-4 flex-shrink-0" />
          )}
          <span className="truncate font-medium">{triggerText}</span>
          {currentSession && (
            <StatusBadge status={currentSession.status} />
          )}
        </div>
        <ChevronUp className={`w-4 h-4 flex-shrink-0 transition-transform ${isOpen ? '' : 'rotate-180'}`} />
      </button>

      {/* Slide-up Panel */}
      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden z-50 max-h-[70vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
            <h3 className="text-sm font-semibold text-gray-900">Select Session</h3>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>

          {/* Search and Filter */}
          <div className="p-3 border-b border-gray-200 space-y-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search sessions..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-gray-400" />
              <div className="flex gap-1">
                {statusOptions.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setStatusFilter(opt.value)}
                    className={`px-2 py-1 text-xs rounded-md transition-colors ${
                      statusFilter === opt.value
                        ? 'bg-primary-100 text-primary-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Session List */}
          <div className="flex-1 overflow-y-auto p-2 min-h-0 max-h-64">
            {filteredSessions.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No sessions found</p>
                <p className="text-xs text-gray-400 mt-1">
                  {search || statusFilter !== 'all'
                    ? 'Try adjusting your filters'
                    : 'Only completed sessions can be selected'}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredSessions.map((session) => (
                  <SessionItem
                    key={session.session_id}
                    session={session}
                    isSelected={session.session_id === currentSessionId}
                    onSelect={() => handleSelectSession(session)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-3 py-2 border-t border-gray-200 text-xs text-gray-500 bg-gray-50">
            {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''} available
          </div>
        </div>
      )}
    </div>
  );
}

// Simplified session item for the selector
interface SessionItemProps {
  session: Session;
  isSelected: boolean;
  onSelect: () => void;
}

function SessionItem({ session, isSelected, onSelect }: SessionItemProps) {
  const displayName = session.session_id.slice(0, 16);
  const projectFolder = session.project_dir ? getLastPathSegment(session.project_dir) : null;

  return (
    <button
      onClick={onSelect}
      className={`w-full flex items-start gap-3 p-2.5 rounded-lg text-left transition-all ${
        isSelected
          ? 'bg-primary-50 ring-1 ring-primary-300'
          : 'hover:bg-gray-50'
      }`}
    >
      {/* Status indicator */}
      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
        session.status === 'finished' ? 'bg-gray-400' : 'bg-amber-500'
      }`} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-gray-900 truncate">{displayName}</span>
          <span className="text-xs text-gray-400 flex-shrink-0">
            {formatRelativeTime(session.modified_at || session.created_at)}
          </span>
        </div>

        <div className="flex items-center gap-3 mt-1">
          {session.agent_name && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Bot className="w-3 h-3" />
              <span className="truncate">{session.agent_name}</span>
            </div>
          )}
          {projectFolder && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Folder className="w-3 h-3" />
              <span className="truncate" title={session.project_dir}>
                {projectFolder}
              </span>
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
