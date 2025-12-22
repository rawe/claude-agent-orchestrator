/**
 * Application configuration loaded from environment variables
 */
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8765';
const apiKey = import.meta.env.VITE_AGENT_ORCHESTRATOR_API_KEY || '';

// SSE endpoint - EventSource doesn't support custom headers, so API key is passed as query param
const sseBaseUrl = `${apiUrl}/sse/sessions`;
const sseUrl = apiKey
  ? `${sseBaseUrl}?api_key=${encodeURIComponent(apiKey)}`
  : sseBaseUrl;

export const config = {
  // API endpoints
  apiUrl,
  // SSE endpoint derived from API URL (ADR-013)
  sseUrl,
  // API authentication
  apiKey,

  // Agent configuration
  agentBlueprint: import.meta.env.VITE_AGENT_BLUEPRINT || 'default-agent',

  // App settings
  appTitle: import.meta.env.VITE_APP_TITLE || 'AI Assistant',
} as const;

export type Config = typeof config;
