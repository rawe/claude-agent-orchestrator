import { useState, useMemo, useRef, useLayoutEffect } from 'react';
import { SessionEvent, EventType } from '@/types';
import { EventCard } from './EventCard';
import { EmptyState, LoadingState } from '@/components/common';
import { getEventKey } from '@/utils';
import {
  Filter,
  ChevronsUpDown,
  ArrowDownToLine,
  Wrench,
  MessageSquare,
  Activity,
} from 'lucide-react';

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

// Get dot color based on event type
function getTimelineDotColor(eventType: EventType, hasError: boolean): string {
  if (hasError) return 'bg-red-500';
  switch (eventType) {
    case 'session_start':
      return 'bg-emerald-500';
    case 'session_stop':
      return 'bg-gray-400';
    case 'pre_tool':
    case 'post_tool':
      return 'bg-blue-500';
    case 'message':
      return 'bg-violet-500';
    default:
      return 'bg-gray-400';
  }
}

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

  // Count events by type
  const eventCounts = useMemo(() => {
    return events.reduce(
      (acc, event) => {
        if (event.event_type === 'pre_tool' || event.event_type === 'post_tool') {
          acc.tools++;
        } else if (event.event_type === 'message') {
          acc.messages++;
        } else if (event.event_type === 'session_start' || event.event_type === 'session_stop') {
          acc.session++;
        }
        return acc;
      },
      { tools: 0, messages: 0, session: 0 }
    );
  }, [events]);

  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  };

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
      {/* Toolbar */}
      <div className="flex-shrink-0 flex items-center justify-between gap-4 px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-gray-500">
            <Filter className="w-4 h-4" />
            <span className="text-sm font-medium">Filter</span>
          </div>
          <div className="flex gap-1">
            <FilterChip
              icon={<Wrench className="w-3.5 h-3.5" />}
              label="Tools"
              count={eventCounts.tools}
              active={filters.tools}
              onClick={() => toggleFilter('tools')}
              color="blue"
            />
            <FilterChip
              icon={<MessageSquare className="w-3.5 h-3.5" />}
              label="Messages"
              count={eventCounts.messages}
              active={filters.messages}
              onClick={() => toggleFilter('messages')}
              color="violet"
            />
            <FilterChip
              icon={<Activity className="w-3.5 h-3.5" />}
              label="Session"
              count={eventCounts.session}
              active={filters.session}
              onClick={() => toggleFilter('session')}
              color="emerald"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAllExpanded(!allExpanded)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title={allExpanded ? 'Collapse all' : 'Expand all'}
          >
            <ChevronsUpDown className="w-4 h-4" />
            {allExpanded ? 'Collapse' : 'Expand'}
          </button>
          <button
            onClick={handleAutoScrollClick}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
              autoScroll
                ? 'bg-primary-100 text-primary-700 font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
            title={autoScroll ? 'Disable auto-scroll' : 'Enable auto-scroll'}
          >
            <ArrowDownToLine className="w-4 h-4" />
            Auto-scroll
          </button>
        </div>
      </div>

      {/* Events with Timeline */}
      <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto bg-gray-50">
        {filteredEvents.length === 0 ? (
          <div className="h-full flex items-center justify-center p-8">
            <EmptyState
              title="No events to display"
              description={events.length > 0 ? 'Try adjusting your filters' : 'Events will appear here as the session runs'}
            />
          </div>
        ) : (
          <div className="p-4">
            {/* Timeline container */}
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-[19px] top-4 bottom-4 w-0.5 bg-gradient-to-b from-gray-200 via-gray-300 to-gray-200" />

              {/* Events */}
              <div className="space-y-3">
                {filteredEvents.map((event) => {
                  const hasError = !!(event.error || (event.event_type === 'session_stop' && event.exit_code !== 0));
                  const dotColor = getTimelineDotColor(event.event_type, hasError);

                  return (
                    <div key={getEventKey(event)} className="relative flex gap-4">
                      {/* Timeline dot */}
                      <div className="relative z-10 flex-shrink-0 flex items-start pt-4">
                        <div className={`w-2.5 h-2.5 rounded-full ${dotColor} ring-4 ring-gray-50 shadow-sm`} />
                      </div>

                      {/* Event card */}
                      <div className="flex-1 min-w-0">
                        <EventCard event={event} forceExpanded={allExpanded} />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Live indicator at end of timeline */}
              {isRunning && (
                <div className="relative flex gap-4 mt-3">
                  <div className="relative z-10 flex-shrink-0 flex items-center pt-1">
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 ring-4 ring-gray-50 animate-pulse" />
                  </div>
                  <div className="flex items-center gap-2 text-sm text-emerald-600 pt-1">
                    <span className="font-medium">Live</span>
                    <span className="text-gray-400">Waiting for events...</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 px-4 py-2.5 border-t border-gray-200 bg-white flex items-center justify-between">
        <div className="text-sm text-gray-500">
          <span className="font-medium text-gray-700">{filteredEvents.length}</span>
          {filteredEvents.length !== events.length && (
            <span> of {events.length}</span>
          )} events
        </div>
        {isRunning && (
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-sm font-medium text-emerald-600">Session Running</span>
          </div>
        )}
      </div>
    </div>
  );
}

interface FilterChipProps {
  icon: React.ReactNode;
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  color: 'blue' | 'violet' | 'emerald';
}

function FilterChip({ icon, label, count, active, onClick, color }: FilterChipProps) {
  const colorClasses = {
    blue: active
      ? 'bg-blue-100 text-blue-700 border-blue-200'
      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300',
    violet: active
      ? 'bg-violet-100 text-violet-700 border-violet-200'
      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300',
    emerald: active
      ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300',
  };

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border transition-colors ${colorClasses[color]}`}
    >
      {icon}
      {label}
      <span className={`ml-0.5 ${active ? 'opacity-70' : 'opacity-50'}`}>({count})</span>
    </button>
  );
}
