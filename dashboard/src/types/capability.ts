import { MCPServerConfig } from './agent';

/**
 * Summary capability for list view (without full text content).
 */
export interface CapabilitySummary {
  name: string;
  description: string;
  has_text: boolean;
  has_mcp: boolean;
  mcp_server_names: string[];
  created_at: string;
  modified_at: string;
}

/**
 * Full capability representation.
 */
export interface Capability {
  name: string;
  description: string;
  text: string | null;
  mcp_servers: Record<string, MCPServerConfig> | null;
  created_at: string;
  modified_at: string;
}

/**
 * Request body for creating a capability.
 */
export interface CapabilityCreate {
  name: string;
  description: string;
  text?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
}

/**
 * Request body for updating a capability (partial).
 */
export interface CapabilityUpdate {
  description?: string;
  text?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
}
