import { AgentDemands } from './agent';

/**
 * Summary script for list view (without script content).
 */
export interface ScriptSummary {
  name: string;
  description: string;
  script_file: string;
  has_parameters_schema: boolean;
  has_demands: boolean;
  demand_tags: string[];
  created_at: string;
  modified_at: string;
}

/**
 * Full script representation.
 */
export interface Script {
  name: string;
  description: string;
  script_file: string;
  script_content: string;
  parameters_schema: Record<string, unknown> | null;
  demands: AgentDemands | null;
  created_at: string;
  modified_at: string;
}

/**
 * Request body for creating a script.
 */
export interface ScriptCreate {
  name: string;
  description: string;
  script_file: string;
  script_content: string;
  parameters_schema?: Record<string, unknown>;
  demands?: AgentDemands;
}

/**
 * Request body for updating a script (partial).
 */
export interface ScriptUpdate {
  description?: string;
  script_file?: string;
  script_content?: string;
  parameters_schema?: Record<string, unknown>;
  demands?: AgentDemands;
}
