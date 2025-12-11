export type AgentStatus = 'active' | 'inactive';
export type AgentVisibility = 'public' | 'internal' | 'all';

export interface MCPServerStdio {
  type?: 'stdio';
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export interface MCPServerHttp {
  type: 'http';
  url: string;
  headers?: Record<string, string>;
}

export type MCPServerConfig = MCPServerStdio | MCPServerHttp;

export interface Agent {
  name: string;
  description: string;
  system_prompt: string | null;
  mcp_servers: Record<string, MCPServerConfig> | null;
  skills: string[] | null;
  visibility: AgentVisibility;
  status: AgentStatus;
  created_at: string;
  modified_at: string;
}

export interface AgentCreate {
  name: string;
  description: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
  visibility?: AgentVisibility;
}

export interface AgentUpdate {
  description?: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
  visibility?: AgentVisibility;
}

// Visibility options for the UI
export const VISIBILITY_OPTIONS = [
  { value: 'all', label: 'All Contexts', description: 'Visible to both external clients and internal agents (default)' },
  { value: 'public', label: 'External Only', description: 'Entry-point agent for Claude Desktop, MCP clients, users' },
  { value: 'internal', label: 'Internal Only', description: 'Worker agent for the orchestrator framework' },
] as const;

// Predefined skills available for selection
// Set disabled: true for skills not yet implemented
export const SKILLS = [
  { name: 'pdf', label: 'PDF Handler', disabled: true },
  { name: 'xlsx', label: 'Excel Handler', disabled: true },
  { name: 'csv', label: 'CSV Handler', disabled: true },
  { name: 'image', label: 'Image Handler', disabled: true },
  { name: 'context-store', label: 'Context Store', disabled: true },
] as const;
