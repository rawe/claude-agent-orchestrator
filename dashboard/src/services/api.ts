import axios from 'axios';
import { AGENT_ORCHESTRATOR_API_URL, DOCUMENT_SERVER_URL } from '@/utils/constants';

// Axios instance for Agent Orchestrator API (sessions, events, agent blueprints)
export const agentOrchestratorApi = axios.create({
  baseURL: AGENT_ORCHESTRATOR_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Aliases for backward compatibility
export const agentRuntimeApi = agentOrchestratorApi;
export const agentRegistryApi = agentOrchestratorApi;

// Axios instance for context store server
export const documentApi = axios.create({
  baseURL: DOCUMENT_SERVER_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptors for error handling
const handleError = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message;
    console.error('API Error:', message);
    throw new Error(message);
  }
  throw error;
};

agentOrchestratorApi.interceptors.response.use((response) => response, handleError);
documentApi.interceptors.response.use((response) => response, handleError);
