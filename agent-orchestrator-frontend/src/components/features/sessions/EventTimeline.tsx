import { useState, useMemo, useEffect, useRef } from 'react';
import { SessionEvent } from '@/types';
import { EventCard } from './EventCard';
import { EmptyState, LoadingState } from '@/components/common';
import { getEventKey } from '@/utils';
import { ListFilter, ChevronsUpDown, ArrowDownToLine } from 'lucide-react';

interface EventTimelineProps {
  events: SessionEvent[];
  loading?: boolean;
  isRunning?: boolean;
}

type EventFilter = {
  tools: boolean;
  messages: boolean;
  session: boolean;
};

export function EventTimeline({ events, loading = false, isRunning = false }: EventTimelineProps) {
  const [filters, setFilters] = useState<EventFilter>({
    tools: true,
    messages: true,
    session: true,
  });
  const [allExpanded, setAllExpanded] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (event.event_type === 'pre_tool' || event.event_type === 'post_tool') {
        return filters.tools;
      }
      if (event.event_type === 'message') {
        return filters.messages;
      }
      if (event.event_type === 'session_start' || event.event_type === 'session_stop') {
        return filters.session;
      }
      return true;
    });
  }, [events, filters]);

  // Auto-scroll to bottom when new events come in
  useEffect(() => {
    if (autoScroll && isRunning && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredEvents.length, autoScroll, isRunning]);

  const toggleFilter = (key: keyof EventFilter) => {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return <LoadingState message="Loading events..." />;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-2">
          <ListFilter className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-500">Filter:</span>
          <div className="flex gap-1">
            <FilterToggle
              label="Tools"
              active={filters.tools}
              onClick={() => toggleFilter('tools')}
            />
            <FilterToggle
              label="Messages"
              active={filters.messages}
              onClick={() => toggleFilter('messages')}
            />
            <FilterToggle
              label="Session"
              active={filters.session}
              onClick={() => toggleFilter('session')}
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAllExpanded(!allExpanded)}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded transition-colors"
            title={allExpanded ? 'Collapse all' : 'Expand all'}
          >
            <ChevronsUpDown className="w-3.5 h-3.5" />
            {allExpanded ? 'Collapse' : 'Expand'}
          </button>
          {isRunning && (
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
                autoScroll
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
              title={autoScroll ? 'Disable auto-scroll' : 'Enable auto-scroll'}
            >
              <ArrowDownToLine className="w-3.5 h-3.5" />
              Auto-scroll
            </button>
          )}
        </div>
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredEvents.length === 0 ? (
          <EmptyState
            title="No events to display"
            description={events.length > 0 ? 'Try adjusting your filters' : 'Events will appear here as the session runs'}
          />
        ) : (
          <>
            {filteredEvents.map((event) => (
              <EventCard key={getEventKey(event)} event={event} defaultExpanded={allExpanded} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Event count */}
      <div className="px-4 py-2 border-t border-gray-200 text-xs text-gray-500 bg-white">
        {filteredEvents.length} of {events.length} events
        {isRunning && <span className="ml-2 text-green-600">● Live</span>}
      </div>
    </div>
  );
}

function FilterToggle({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-2 py-1 text-xs rounded transition-colors ${
        active
          ? 'bg-primary-100 text-primary-700 font-medium'
          : 'text-gray-500 hover:bg-gray-100'
      }`}
    >
      {label}
    </button>
  );
}
