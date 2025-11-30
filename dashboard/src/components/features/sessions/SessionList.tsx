import { useState, useMemo } from 'react';
import { Session, SessionStatus } from '@/types';
import { SessionCard } from './SessionCard';
import { EmptyState, SkeletonCard } from '@/components/common';
import { Activity, Search, Filter, ArrowUpDown } from 'lucide-react';

interface SessionListProps {
  sessions: Session[];
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onStopSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  loading?: boolean;
}

type SortOption = 'modified_desc' | 'modified_asc' | 'created_desc' | 'created_asc';

const statusOptions: { value: SessionStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Status' },
  { value: 'running', label: 'Running' },
  { value: 'finished', label: 'Finished' },
  { value: 'stopped', label: 'Stopped' },
];

const sortOptions: { value: SortOption; label: string }[] = [
  { value: 'modified_desc', label: 'Modified (Newest)' },
  { value: 'modified_asc', label: 'Modified (Oldest)' },
  { value: 'created_desc', label: 'Created (Newest)' },
  { value: 'created_asc', label: 'Created (Oldest)' },
];

export function SessionList({
  sessions,
  selectedSessionId,
  onSelectSession,
  onStopSession,
  onDeleteSession,
  loading = false,
}: SessionListProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>('all');
  const [sortBy, setSortBy] = useState<SortOption>('modified_desc');

  const filteredSessions = useMemo(() => {
    let filtered = [...sessions];

    // Filter by search
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(
        (s) =>
          s.session_name?.toLowerCase().includes(searchLower) ||
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
      switch (sortBy) {
        case 'modified_desc':
          return (
            new Date(b.modified_at || b.created_at).getTime() -
            new Date(a.modified_at || a.created_at).getTime()
          );
        case 'modified_asc':
          return (
            new Date(a.modified_at || a.created_at).getTime() -
            new Date(b.modified_at || b.created_at).getTime()
          );
        case 'created_desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'created_asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        default:
          return 0;
      }
    });

    return filtered;
  }, [sessions, search, statusFilter, sortBy]);

  if (loading) {
    return (
      <div className="space-y-3 p-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filters */}
      <div className="p-3 border-b border-gray-200 space-y-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search sessions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as SessionStatus | 'all')}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="relative flex-1">
            <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              {sortOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filteredSessions.length === 0 ? (
          <EmptyState
            icon={<Activity className="w-12 h-12" />}
            title="No sessions found"
            description={search || statusFilter !== 'all' ? 'Try adjusting your filters' : 'Sessions will appear here when agents start running'}
          />
        ) : (
          filteredSessions.map((session) => (
            <SessionCard
              key={session.session_id}
              session={session}
              isSelected={session.session_id === selectedSessionId}
              onSelect={() => onSelectSession(session.session_id)}
              onStop={session.status === 'running' ? () => onStopSession(session.session_id) : undefined}
              onDelete={() => onDeleteSession(session.session_id)}
            />
          ))
        )}
      </div>

      {/* Count */}
      <div className="px-3 py-2 border-t border-gray-200 text-xs text-gray-500">
        {filteredSessions.length} of {sessions.length} sessions
      </div>
    </div>
  );
}
