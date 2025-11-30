import { useState, useMemo, useRef, useLayoutEffect } from 'react';
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
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const prevEventsLengthRef = useRef<number>(0);
  const prevFirstEventIdRef = useRef<string | undefined>(undefined);

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

  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  };

  // Detect session change (different events array) or new events added
  useLayoutEffect(() => {
    const firstEventId = events[0]?.session_id;
    const sessionChanged = firstEventId !== prevFirstEventIdRef.current;
    const eventsAdded = events.length > prevEventsLengthRef.current;

    if (autoScroll && (sessionChanged || eventsAdded)) {
      scrollToBottom();
    }

    prevEventsLengthRef.current = events.length;
    prevFirstEventIdRef.current = firstEventId;
  }, [events, autoScroll]);

  const handleAutoScrollClick = () => {
    const newState = !autoScroll;
    setAutoScroll(newState);
    if (newState) {
      scrollToBottom();
    }
  };

  const toggleFilter = (key: keyof EventFilter) => {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return <LoadingState message="Loading events..." />;
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Toolbar - always visible, never shrinks */}
      <div className="flex-shrink-0 flex items-center justify-between gap-4 p-4 border-b border-gray-200 bg-white">
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
          <button
            onClick={handleAutoScrollClick}
            className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
              autoScroll
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
            title={autoScroll ? 'Disable auto-scroll (click to scroll to bottom)' : 'Enable auto-scroll and scroll to bottom'}
          >
            <ArrowDownToLine className="w-3.5 h-3.5" />
            Auto-scroll
          </button>
        </div>
      </div>

      {/* Events - scrollable area */}
      <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
        {filteredEvents.length === 0 ? (
          <EmptyState
            title="No events to display"
            description={events.length > 0 ? 'Try adjusting your filters' : 'Events will appear here as the session runs'}
          />
        ) : (
          filteredEvents.map((event) => (
            <EventCard key={getEventKey(event)} event={event} forceExpanded={allExpanded} />
          ))
        )}
      </div>

      {/* Event count - always visible, never shrinks */}
      <div className="flex-shrink-0 px-4 py-2 border-t border-gray-200 text-xs text-gray-500 bg-white">
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
