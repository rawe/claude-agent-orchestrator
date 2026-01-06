import { useState, useEffect } from 'react';
import { SessionEvent, EventType } from '@/types';
import { formatTime } from '@/utils/formatters';
import {
  ChevronDown,
  ChevronRight,
  Play,
  Square,
  Wrench,
  CheckCircle2,
  MessageSquare,
  Copy,
  Check,
  AlertCircle,
  User,
  Bot,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface EventCardProps {
  event: SessionEvent;
  forceExpanded?: boolean;
}

type EventConfig = {
  icon: React.ElementType;
  accentColor: string;
  bgColor: string;
  iconBg: string;
  iconColor: string;
  label: string;
};

const eventConfig: Record<EventType, EventConfig> = {
  run_start: {
    icon: Play,
    accentColor: 'bg-emerald-500',
    bgColor: 'bg-white',
    iconBg: 'bg-emerald-100',
    iconColor: 'text-emerald-600',
    label: 'Run Started',
  },
  run_completed: {
    icon: Square,
    accentColor: 'bg-gray-400',
    bgColor: 'bg-white',
    iconBg: 'bg-gray-100',
    iconColor: 'text-gray-600',
    label: 'Run Completed',
  },
  pre_tool: {
    icon: Wrench,
    accentColor: 'bg-blue-500',
    bgColor: 'bg-white',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    label: 'Tool Call',
  },
  post_tool: {
    icon: CheckCircle2,
    accentColor: 'bg-blue-500',
    bgColor: 'bg-white',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    label: 'Tool Result',
  },
  message: {
    icon: MessageSquare,
    accentColor: 'bg-violet-500',
    bgColor: 'bg-white',
    iconBg: 'bg-violet-100',
    iconColor: 'text-violet-600',
    label: 'Message',
  },
};

function CopyCodeButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
      title="Copy to clipboard"
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

function CodeBlock({ content, variant = 'default' }: { content: string; variant?: 'default' | 'error' | 'success' }) {
  const bgColors = {
    default: 'bg-gray-900',
    error: 'bg-red-950',
    success: 'bg-emerald-950',
  };

  return (
    <div className="relative group rounded-lg overflow-hidden">
      <pre className={`${bgColors[variant]} text-gray-100 p-3 overflow-x-auto text-xs font-mono leading-relaxed max-h-72`}>
        {content}
      </pre>
      <CopyCodeButton text={content} />
    </div>
  );
}

export function EventCard({ event, forceExpanded = false }: EventCardProps) {
  const [expanded, setExpanded] = useState(forceExpanded);

  useEffect(() => {
    setExpanded(forceExpanded);
  }, [forceExpanded]);

  const config = eventConfig[event.event_type] || {
    icon: AlertCircle,
    accentColor: 'bg-gray-400',
    bgColor: 'bg-white',
    iconBg: 'bg-gray-100',
    iconColor: 'text-gray-600',
    label: event.event_type,
  };

  const hasError = event.error || (event.event_type === 'run_completed' && event.exit_code !== 0);
  const Icon = hasError ? AlertCircle : config.icon;
  const accentColor = hasError ? 'bg-red-500' : config.accentColor;
  const iconBg = hasError ? 'bg-red-100' : config.iconBg;
  const iconColor = hasError ? 'text-red-600' : config.iconColor;

  const hasExpandableContent =
    event.event_type === 'pre_tool' ||
    event.event_type === 'post_tool' ||
    (event.event_type === 'message' &&
      event.content?.some((b) => b.type === 'text' && b.text && b.text.length > 200));

  const renderContent = () => {
    switch (event.event_type) {
      case 'run_start':
        return (
          <div className="text-sm text-gray-500">
            Session ID: <span className="font-mono text-gray-700">{event.session_id.slice(0, 12)}...</span>
          </div>
        );

      case 'run_completed':
        return (
          <div className="text-sm space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Exit Code:</span>
              <span className={`font-mono font-medium ${event.exit_code === 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {event.exit_code ?? 'N/A'}
              </span>
            </div>
            {event.reason && (
              <div className="text-gray-500">
                Reason: <span className="text-gray-700">{event.reason}</span>
              </div>
            )}
          </div>
        );

      case 'pre_tool':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                {event.tool_name}
              </span>
              <span className="text-xs text-gray-400">Executing...</span>
            </div>
            {expanded && event.tool_input && (
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Input</div>
                <CodeBlock content={JSON.stringify(event.tool_input, null, 2)} />
              </div>
            )}
          </div>
        );

      case 'post_tool':
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 text-xs font-medium rounded ${hasError ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>
                {event.tool_name}
              </span>
              <span className={`text-xs ${hasError ? 'text-red-500' : 'text-emerald-500'}`}>
                {hasError ? 'Failed' : 'Completed'}
              </span>
            </div>

            {expanded && (
              <div className="space-y-3">
                {/* Input section */}
                {event.tool_input && Object.keys(event.tool_input).length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Input</div>
                    <CodeBlock content={JSON.stringify(event.tool_input, null, 2)} />
                  </div>
                )}

                {/* Error or Output section */}
                {hasError && event.error ? (
                  <div className="space-y-1.5">
                    <div className="text-xs font-medium text-red-500 uppercase tracking-wide">Error</div>
                    <CodeBlock content={event.error} variant="error" />
                  </div>
                ) : event.tool_output !== undefined && event.tool_output !== null ? (
                  <div className="space-y-1.5">
                    <div className="text-xs font-medium text-emerald-600 uppercase tracking-wide">Output</div>
                    <CodeBlock
                      content={typeof event.tool_output === 'string' ? event.tool_output : JSON.stringify(event.tool_output, null, 2)}
                      variant="success"
                    />
                  </div>
                ) : null}
              </div>
            )}
          </div>
        );

      case 'message':
        const isUser = event.role === 'user';
        return (
          <div className="space-y-2">
            {/* Role badge */}
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full ${
                isUser
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-violet-100 text-violet-700'
              }`}>
                {isUser ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                {isUser ? 'User' : 'Assistant'}
              </span>
            </div>

            {/* Message content */}
            <div className="prose prose-sm max-w-none text-gray-700">
              {event.content?.map((block, i) => {
                if (block.type === 'text' && block.text) {
                  const text = expanded ? block.text : block.text.slice(0, 200) + (block.text.length > 200 ? '...' : '');
                  return (
                    <div key={i} className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
                    </div>
                  );
                }
                if (block.type === 'tool_use') {
                  return (
                    <div key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-600 text-xs rounded">
                      <Wrench className="w-3 h-3" />
                      Using: {block.name}
                    </div>
                  );
                }
                if (block.type === 'tool_result') {
                  return (
                    <div key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                      <CheckCircle2 className="w-3 h-3" />
                      Tool result
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

  return (
    <div className={`relative flex rounded-lg overflow-hidden ${config.bgColor} shadow-sm hover:shadow-md transition-shadow duration-200 border border-gray-100`}>
      {/* Accent bar */}
      <div className={`w-1 ${accentColor} flex-shrink-0`} />

      {/* Main content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <button
          onClick={() => hasExpandableContent && setExpanded(!expanded)}
          className={`w-full flex items-center gap-3 px-4 py-3 text-left ${
            hasExpandableContent ? 'cursor-pointer hover:bg-gray-50' : 'cursor-default'
          } transition-colors`}
        >
          {/* Icon */}
          <div className={`flex-shrink-0 w-8 h-8 rounded-lg ${iconBg} flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${iconColor}`} />
          </div>

          {/* Label and time */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">{config.label}</span>
              {event.tool_name && event.event_type !== 'pre_tool' && event.event_type !== 'post_tool' && (
                <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                  {event.tool_name}
                </span>
              )}
            </div>
            <span className="text-xs text-gray-400">{formatTime(event.timestamp)}</span>
          </div>

          {/* Expand indicator */}
          {hasExpandableContent && (
            <div className="flex-shrink-0 text-gray-400">
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </div>
          )}
        </button>

        {/* Content */}
        <div className={`px-4 pb-3 ${hasExpandableContent ? 'pl-[60px]' : 'pl-[60px]'}`}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
