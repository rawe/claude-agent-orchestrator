/**
 * Constants for Agent Orchestrator MCP Server
 */

// Environment variable names
export const ENV_SCRIPT_PATH = "AGENT_ORCHESTRATOR_SCRIPT_PATH";

// Session name constraints (from agent-orchestrator.sh)
export const MAX_SESSION_NAME_LENGTH = 60;
export const SESSION_NAME_PATTERN = /^[a-zA-Z0-9_-]+$/;

// Character limit for responses
export const CHARACTER_LIMIT = 25000;