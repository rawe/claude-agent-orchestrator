import axios from 'axios';
import { AGENT_ORCHESTRATOR_API_URL, AGENT_ORCHESTRATOR_API_KEY, DOCUMENT_SERVER_URL } from '@/utils/constants';
import { fetchAccessToken, isOidcConfigured } from './auth';

// Axios instance for Agent Orchestrator API (sessions, events, agent blueprints, runs)
export const agentOrchestratorApi = axios.create({
  baseURL: AGENT_ORCHESTRATOR_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
agentOrchestratorApi.interceptors.request.use(async (config) => {
  // Try OIDC token first if configured
  if (isOidcConfigured()) {
    const token = await fetchAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    }
  }

  // Fall back to static API key
  if (AGENT_ORCHESTRATOR_API_KEY) {
    config.headers.Authorization = `Bearer ${AGENT_ORCHESTRATOR_API_KEY}`;
  }

  return config;
});

// Axios instance for context store server
export const documentApi = axios.create({
  baseURL: DOCUMENT_SERVER_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptors for error handling with auth-specific messages
const handleError = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;

    // Auth-specific error messages
    if (status === 401) {
      const message = 'Authentication required. Check VITE_AGENT_ORCHESTRATOR_API_KEY.';
      console.error('API Error:', message);
      throw new Error(message);
    }
    if (status === 403) {
      const message = 'Access denied. Invalid API key.';
      console.error('API Error:', message);
      throw new Error(message);
    }

    const message = error.response?.data?.detail || error.response?.data?.message || error.message;
    console.error('API Error:', message);
    throw new Error(message);
  }
  throw error;
};

agentOrchestratorApi.interceptors.response.use((response) => response, handleError);
documentApi.interceptors.response.use((response) => response, handleError);
