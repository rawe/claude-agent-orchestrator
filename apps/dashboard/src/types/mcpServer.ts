// ==============================================================================
// MCP Server Registry Types
// ==============================================================================

/**
 * Schema definition for a single config field.
 * Used to define what config parameters an MCP server expects.
 */
export interface ConfigSchemaField {
  type: 'string' | 'integer' | 'boolean';
  description?: string;
  required: boolean;
  sensitive: boolean;  // If true, value should be masked in logs/UI
  default?: unknown;
}

/**
 * Type alias for config schema - maps field names to their definitions.
 */
export type MCPServerConfigSchema = Record<string, ConfigSchemaField>;

/**
 * Full MCP server registry entry as returned by the API.
 */
export interface MCPServerRegistryEntry {
  id: string;
  name: string;
  description?: string;
  url: string;
  config_schema?: MCPServerConfigSchema;
  default_config?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * Request body for creating an MCP server registry entry.
 */
export interface MCPServerRegistryCreate {
  id: string;
  name: string;
  description?: string;
  url: string;
  config_schema?: MCPServerConfigSchema;
  default_config?: Record<string, unknown>;
}

/**
 * Request body for updating an MCP server registry entry (partial).
 */
export interface MCPServerRegistryUpdate {
  name?: string;
  description?: string;
  url?: string;
  config_schema?: MCPServerConfigSchema;
  default_config?: Record<string, unknown>;
}
