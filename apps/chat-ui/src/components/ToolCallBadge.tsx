import { useState } from 'react';
import { Wrench, Check, X, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import type { ToolCall } from '../types';

interface ToolCallBadgeProps {
  tool: ToolCall;
}

// Helper to format output for display
function formatOutput(output: unknown): string {
  if (typeof output === 'string') {
    return output.length > 500 ? output.substring(0, 500) + '...' : output;
  }
  const str = JSON.stringify(output, null, 2);
  return str.length > 500 ? str.substring(0, 500) + '...' : str;
}

export function ToolCallBadge({ tool }: ToolCallBadgeProps) {
  const [expanded, setExpanded] = useState(false);

  const statusConfig = {
    running: {
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      textColor: 'text-blue-700',
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
      label: 'Running',
    },
    completed: {
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      textColor: 'text-green-700',
      icon: <Check className="w-3 h-3" />,
      label: 'Done',
    },
    error: {
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
      textColor: 'text-red-700',
      icon: <X className="w-3 h-3" />,
      label: 'Error',
    },
  };

  const config = statusConfig[tool.status];
  const hasDetails = tool.input || tool.output || tool.error;

  return (
    <div className={`rounded-lg border ${config.borderColor} ${config.bgColor} overflow-hidden`}>
      {/* Badge header */}
      <button
        onClick={() => hasDetails && setExpanded(!expanded)}
        disabled={!hasDetails}
        className={`
          flex items-center gap-2 px-3 py-1.5 w-full text-left
          ${hasDetails ? 'hover:bg-black/5 cursor-pointer' : 'cursor-default'}
          transition-colors
        `}
      >
        <Wrench className={`w-3.5 h-3.5 ${config.textColor}`} />
        <span className={`text-sm font-medium ${config.textColor}`}>
          {tool.name}
        </span>
        <span className={`flex items-center gap-1 text-xs ${config.textColor} opacity-75 ${tool.status === 'running' ? 'tool-running' : ''}`}>
          {config.icon}
          {config.label}
        </span>
        {hasDetails && (
          <span className={`ml-auto ${config.textColor}`}>
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </span>
        )}
      </button>

      {/* Expanded details */}
      {expanded && hasDetails && (
        <div className={`border-t ${config.borderColor} px-3 py-2 text-xs space-y-2 bg-white/50`}>
          {tool.input && Object.keys(tool.input).length > 0 && (
            <div>
              <span className="font-medium text-gray-600">Input:</span>
              <pre className="mt-1 p-2 bg-gray-100 rounded text-gray-700 overflow-x-auto max-h-32">
                {JSON.stringify(tool.input, null, 2)}
              </pre>
            </div>
          )}
          {tool.output !== undefined && (
            <div>
              <span className="font-medium text-gray-600">Output:</span>
              <pre className="mt-1 p-2 bg-gray-100 rounded text-gray-700 overflow-x-auto max-h-32">
                {formatOutput(tool.output)}
              </pre>
            </div>
          )}
          {tool.error && (
            <div>
              <span className="font-medium text-red-600">Error:</span>
              <pre className="mt-1 p-2 bg-red-50 rounded text-red-700 overflow-x-auto">
                {tool.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
