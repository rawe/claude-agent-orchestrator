export type AgentStatus = 'active' | 'inactive';

// Agent Demands (ADR-011)
// Requirements the agent demands to be satisfied before a session can run
export interface AgentDemands {
  hostname?: string;      // Must run on this specific host
  project_dir?: string;   // Must run in this directory
  executor_type?: string; // Must use this executor type
  tags?: string[];        // Must have ALL these capability tags
}

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
  tags: string[];
  demands: AgentDemands | null;
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
  tags?: string[];
  demands?: AgentDemands | null;
}

export interface AgentUpdate {
  description?: string;
  system_prompt?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
  skills?: string[];
  tags?: string[];
  demands?: AgentDemands | null;
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
