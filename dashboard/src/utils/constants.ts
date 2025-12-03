// API URLs from environment variables
export const AGENT_RUNTIME_URL = import.meta.env.VITE_AGENT_RUNTIME_URL || 'http://localhost:8765';
export const DOCUMENT_SERVER_URL = import.meta.env.VITE_DOCUMENT_SERVER_URL || 'http://localhost:8766';
export const AGENT_REGISTRY_URL = import.meta.env.VITE_AGENT_REGISTRY_URL || 'http://localhost:8767';
export const AGENT_ORCHESTRATOR_URL = import.meta.env.VITE_AGENT_ORCHESTRATOR_URL || 'http://localhost:9500';
export const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8765/ws';

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

// WebSocket reconnection
export const WS_RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];
