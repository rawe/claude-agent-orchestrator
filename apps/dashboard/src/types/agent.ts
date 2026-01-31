export type AgentStatus = 'active' | 'inactive';

// Agent type: autonomous agents interpret intent, procedural agents follow defined procedures
export type AgentType = 'autonomous' | 'procedural';

// ==============================================================================
// Agent Hook Types (Agent Run Hooks)
// ==============================================================================

// Behavior when a hook fails or times out
export type HookOnError = 'block' | 'continue';

// Configuration for an agent-type hook
export interface HookAgentConfig {
  type: 'agent';
  agent_name: string;
  on_error: HookOnError;
  timeout_seconds?: number; // Default: 300 (5 minutes)
}

// Union type for future extensibility
export type HookConfig = HookAgentConfig;

// Lifecycle hooks for an agent
export interface AgentHooks {
  on_run_start?: HookConfig | null;
  on_run_finish?: HookConfig | null;
}

// ==============================================================================
// Agent Demands (ADR-011)
// Requirements the agent demands to be satisfied before a session can run
export interface AgentDemands {
  hostname?: string;          // Must run on this specific host
  project_dir?: string;       // Must run in this directory
  executor_profile?: string;  // Must use this executor profile
  tags?: string[];            // Must have ALL these capability tags
}

// ==============================================================================
// MCP Server Config Types
// ==============================================================================

/**
 * MCP server configuration for stdio transport (command-based).
 * Used for local MCP servers like Playwright.
 */
export interface MCPServerStdio {
  type?: 'stdio';
  command: string;
  args: string[];
  env?: Record<string, string>;
}

/**
 * Reference to an MCP server in the registry.
 * Used in agent/capability mcp_servers config instead of inline type/url.
 * This is the preferred format for HTTP-based MCP servers.
 */
export interface MCPServerRef {
  ref: string;  // Registry entry ID
  config?: Record<string, unknown>;  // Config values to merge with defaults
}

/**
 * MCP server configuration - can be either:
 * - MCPServerStdio: For local command-based servers (e.g., Playwright)
 * - MCPServerRef: Reference to a server in the registry (preferred for HTTP servers)
 */
export type MCPServerConfig = MCPServerStdio | MCPServerRef;

/**
 * Type guard to check if an MCP server config is a registry reference.
 */
export function isMCPServerRef(config: MCPServerConfig): config is MCPServerRef {
  return 'ref' in config;
}

/**
 * Type guard to check if an MCP server config is a stdio server.
 */
export function isMCPServerStdio(config: MCPServerConfig): config is MCPServerStdio {
  return 'command' in config;
}

export interface Agent {
  name: string;
  description: string;
  type: AgentType;
  parameters_schema: Record<string, unknown> | null;  // JSON Schema for parameter validation
  output_schema: Record<string, unknown> | null;  // JSON Schema for output validation
  system_prompt: string | null;
  mcp_servers: Record<string, MCPServerConfig> | null;
  skills: string[] | null;
  tags: string[];
  capabilities: string[];
  demands: AgentDemands | null;
  hooks: AgentHooks | null;  // Lifecycle hooks
  status: AgentStatus;
  created_at: string;
  modified_at: string;
  // Runner-owned agent fields (Phase 4 - Procedural Executor)
  command?: string | null;      // CLI command for procedural agents
  runner_id?: string | null;    // Runner that owns this agent (null = file-based)
  // Script reference for procedural agents
  script?: string | null;       // Script name for procedural agents
}

// Helper to check if agent is runner-owned (read-only in UI)
export function isRunnerOwned(agent: Agent): boolean {
  return agent.runner_id != null;
}

export interface AgentCreate {
  name: string;
  description: string;
  type?: AgentType;  // Defaults to 'autonomous'
  script?: string;   // Script name for procedural agents
  parameters_schema?: Record<string, unknown> | null;  // JSON Schema for parameter validation
  output_schema?: Record<string, unknown> | null;  // JSON Schema for output validation
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
  tags?: string[];
  capabilities?: string[];
  demands?: AgentDemands | null;
  hooks?: AgentHooks | null;  // Lifecycle hooks
}

export interface AgentUpdate {
  type?: AgentType;
  script?: string;   // Script name for procedural agents
  parameters_schema?: Record<string, unknown> | null;  // JSON Schema for parameter validation
  output_schema?: Record<string, unknown> | null;  // JSON Schema for output validation
  description?: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
  tags?: string[];
  capabilities?: string[];
  demands?: AgentDemands | null;
  hooks?: AgentHooks | null;  // Lifecycle hooks
}

// Predefined skills available for selection
// Set disabled: true for skills not yet implemented
export const SKILLS = [
  { name: 'pdf', label: 'PDF Handler', disabled: true },
  { name: 'xlsx', label: 'Excel Handler', disabled: true },
  { name: 'csv', label: 'CSV Handler', disabled: true },
  { name: 'image', label: 'Image Handler', disabled: true },
  { name: 'context-store', label: 'Context Store', disabled: true },
] as const;
