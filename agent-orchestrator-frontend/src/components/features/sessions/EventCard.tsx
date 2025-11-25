import { useState, useEffect } from 'react';
import { SessionEvent, EventType } from '@/types';
import { formatTime } from '@/utils/formatters';
import { ChevronDown, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface EventCardProps {
  event: SessionEvent;
  forceExpanded?: boolean;
}

const eventConfig: Record<EventType, { icon: string; color: string; label: string }> = {
  session_start: { icon: '🚀', color: 'bg-green-50 border-green-200', label: 'Session Start' },
  session_stop: { icon: '🏁', color: 'bg-gray-50 border-gray-200', label: 'Session Stop' },
  pre_tool: { icon: '🔧', color: 'bg-blue-50 border-blue-200', label: 'Tool Call' },
  post_tool: { icon: '✅', color: 'bg-blue-50 border-blue-200', label: 'Tool Result' },
  message: { icon: '💬', color: 'bg-purple-50 border-purple-200', label: 'Message' },
};

export function EventCard({ event, forceExpanded = false }: EventCardProps) {
  const [expanded, setExpanded] = useState(forceExpanded);

  // Sync with parent's force expanded state
  useEffect(() => {
    setExpanded(forceExpanded);
  }, [forceExpanded]);
  const config = eventConfig[event.event_type] || {
    icon: '❓',
    color: 'bg-gray-50 border-gray-200',
    label: event.event_type,
  };

  const hasError = event.error || (event.event_type === 'session_stop' && event.exit_code !== 0);
  const borderColor = hasError ? 'border-red-300 bg-red-50' : config.color;

  const renderContent = () => {
    switch (event.event_type) {
      case 'session_start':
        return (
          <div className="text-sm text-gray-600">
            <p>Session ID: {event.session_id}</p>
          </div>
        );

      case 'session_stop':
        return (
          <div className="text-sm text-gray-600">
            <p>Exit Code: {event.exit_code ?? 'N/A'}</p>
            {event.reason && <p>Reason: {event.reason}</p>}
          </div>
        );

      case 'pre_tool':
        return (
          <div className="text-sm">
            <p className="font-medium text-gray-700 mb-1">Tool: {event.tool_name}</p>
            {expanded && event.tool_input && (
              <pre className="bg-gray-900 text-gray-100 p-3 rounded-md overflow-x-auto text-xs">
                {JSON.stringify(event.tool_input, null, 2)}
              </pre>
            )}
          </div>
        );

      case 'post_tool':
        return (
          <div className="text-sm">
            <p className="font-medium text-gray-700 mb-1">
              Tool: {event.tool_name}
              {hasError && <span className="text-red-600 ml-2">Failed</span>}
            </p>
            {/* Input section */}
            {expanded && event.tool_input && Object.keys(event.tool_input).length > 0 && (
              <div className="mt-2">
                <p className="text-xs text-gray-500 mb-1 font-medium">Input:</p>
                <pre className="bg-gray-100 text-gray-800 p-3 rounded-md overflow-x-auto text-xs">
                  {JSON.stringify(event.tool_input, null, 2)}
                </pre>
              </div>
            )}
            {/* Error or Output section */}
            {expanded && (
              hasError && event.error ? (
                <div className="mt-2">
                  <p className="text-xs text-red-600 mb-1 font-medium">Error:</p>
                  <pre className="bg-red-50 text-red-700 p-3 rounded-md overflow-x-auto text-xs">
                    {event.error}
                  </pre>
                </div>
              ) : event.tool_output !== undefined && event.tool_output !== null && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500 mb-1 font-medium">Output:</p>
                  <pre className="bg-green-50 text-gray-800 p-3 rounded-md overflow-x-auto text-xs max-h-64">
                    {typeof event.tool_output === 'string'
                      ? event.tool_output
                      : JSON.stringify(event.tool_output, null, 2)}
                  </pre>
                </div>
              )
            )}
          </div>
        );

      case 'message':
        return (
          <div className="text-sm">
            <p className="font-medium text-gray-700 mb-1 flex items-center gap-2">
              {event.role === 'user' ? '👤 User' : '🤖 Assistant'}
            </p>
            <div className="markdown-content">
              {event.content?.map((block, i) => {
                if (block.type === 'text' && block.text) {
                  return (
                    <ReactMarkdown key={i}>
                      {expanded ? block.text : block.text.slice(0, 200) + (block.text.length > 200 ? '...' : '')}
                    </ReactMarkdown>
                  );
                }
                if (block.type === 'tool_use') {
                  return (
                    <div key={i} className="text-xs text-gray-500 italic">
                      [Tool use: {block.name}]
                    </div>
                  );
                }
                if (block.type === 'tool_result') {
                  return (
                    <div key={i} className="text-xs text-gray-500 italic">
                      [Tool result]
                    </div>
                  );
                }
                return null;
              })}
            </div>
          </div>
        );

      default:
        return <pre className="text-xs">{JSON.stringify(event, null, 2)}</pre>;
    }
  };

  const hasExpandableContent =
    event.event_type === 'pre_tool' ||
    event.event_type === 'post_tool' ||
    (event.event_type === 'message' &&
      event.content?.some((b) => b.type === 'text' && b.text && b.text.length > 200));

  return (
    <div className={`border rounded-lg ${borderColor}`}>
      <button
        onClick={() => hasExpandableContent && setExpanded(!expanded)}
        className={`w-full flex items-center gap-3 px-4 py-3 text-left ${
          hasExpandableContent ? 'cursor-pointer hover:bg-white/50' : 'cursor-default'
        }`}
      >
        <span className="text-lg">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900">{config.label}</span>
            {event.tool_name && (
              <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                {event.tool_name}
              </span>
            )}
          </div>
          <span className="text-xs text-gray-500">{formatTime(event.timestamp)}</span>
        </div>
        {hasExpandableContent && (
          <span className="text-gray-400">
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </span>
        )}
      </button>

      <div className="px-4 pb-3">{renderContent()}</div>
    </div>
  );
}
