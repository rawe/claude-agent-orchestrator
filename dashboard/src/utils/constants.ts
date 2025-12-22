// API URLs from environment variables
// Agent Orchestrator API handles sessions, events, agent blueprints, and runs (unified service)
export const AGENT_ORCHESTRATOR_API_URL = import.meta.env.VITE_AGENT_ORCHESTRATOR_API_URL || 'http://localhost:8765';
export const DOCUMENT_SERVER_URL = import.meta.env.VITE_DOCUMENT_SERVER_URL || 'http://localhost:8766';

// API authentication
export const AGENT_ORCHESTRATOR_API_KEY = import.meta.env.VITE_AGENT_ORCHESTRATOR_API_KEY || '';

// SSE endpoint for real-time updates (ADR-013) - derived from API URL
// Note: EventSource doesn't support custom headers, so API key is passed as query param
const sseBaseUrl = `${AGENT_ORCHESTRATOR_API_URL}/sse/sessions`;
export const SSE_URL = AGENT_ORCHESTRATOR_API_KEY
  ? `${sseBaseUrl}?api_key=${encodeURIComponent(AGENT_ORCHESTRATOR_API_KEY)}`
  : sseBaseUrl;

// Status colors
export const STATUS_COLORS = {
  running: 'bg-green-100 text-green-800',
  finished: 'bg-blue-100 text-blue-800',
  stopped: 'bg-red-100 text-red-800',
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-600',
} as const;

// Status icons (emoji)
export const STATUS_ICONS = {
  running: '🟢',
  finished: '✅',
  stopped: '🛑',
  active: '🟢',
  inactive: '⚫',
} as const;

// Event type icons
export const EVENT_ICONS = {
  session_start: '🚀',
  session_stop: '🏁',
  pre_tool: '🔧',
  post_tool: '✅',
  message: '💬',
} as const;

// File type icons
export const FILE_ICONS: Record<string, string> = {
  'text/markdown': '📝',
  'application/json': '📊',
  'text/plain': '📄',
  'application/pdf': '📕',
  'image/png': '🖼️',
  'image/jpeg': '🖼️',
  'text/csv': '📈',
  default: '📎',
};

// Pagination
export const DEFAULT_PAGE_SIZE = 50;
