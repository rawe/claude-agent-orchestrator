export type AgentStatus = 'active' | 'inactive';

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
}

export interface AgentUpdate {
  description?: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
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
