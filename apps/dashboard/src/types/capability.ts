import { MCPServerConfig } from './agent';

/**
 * Type of capability - determines which fields are allowed.
 *
 * - script: Local script execution (script field allowed, mcp_servers forbidden)
 * - mcp: MCP server integration (mcp_servers field allowed, script forbidden)
 * - text: Instructions only (both script and mcp_servers forbidden)
 *
 * The text field is always allowed for additional instructions.
 */
export type CapabilityType = 'script' | 'mcp' | 'text';

/**
 * Summary capability for list view (without full text content).
 */
export interface CapabilitySummary {
  name: string;
  description: string;
  type: CapabilityType;
  has_script: boolean;
  script_name: string | null;
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
  type: CapabilityType;
  script: string | null;
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
  type: CapabilityType;
  script?: string;
  text?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
}

/**
 * Request body for updating a capability (partial).
 */
export interface CapabilityUpdate {
  description?: string;
  type?: CapabilityType;
  script?: string;
  text?: string;
  mcp_servers?: Record<string, MCPServerConfig> | null;
}
