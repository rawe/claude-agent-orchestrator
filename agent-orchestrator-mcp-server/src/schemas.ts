/**
 * Zod validation schemas for Agent Orchestrator MCP Server
 */

import { z } from "zod";
import { ResponseFormat } from "./types.js";
import { MAX_SESSION_NAME_LENGTH, SESSION_NAME_PATTERN } from "./constants.js";

// Base schema for response format
const ResponseFormatSchema = z.nativeEnum(ResponseFormat)
  .default(ResponseFormat.MARKDOWN)
  .describe("Output format: 'markdown' for human-readable or 'json' for machine-readable");

// Base schema for project directory (reused across all tools)
const ProjectDirSchema = z.string()
  .optional()
  .describe("Optional project directory path (must be absolute path). Only set when instructed to set a project dir!");

// Schema for list_agents tool
export const ListAgentsInputSchema = z.object({
  project_dir: ProjectDirSchema,
  response_format: ResponseFormatSchema
}).strict();

export type ListAgentsInput = z.infer<typeof ListAgentsInputSchema>;

// Schema for list_sessions tool
export const ListSessionsInputSchema = z.object({
  project_dir: ProjectDirSchema,
  response_format: ResponseFormatSchema
}).strict();

export type ListSessionsInput = z.infer<typeof ListSessionsInputSchema>;

// Schema for start_agent tool
export const StartAgentInputSchema = z.object({
  session_name: z.string()
    .min(1, "Session name cannot be empty")
    .max(MAX_SESSION_NAME_LENGTH, `Session name must not exceed ${MAX_SESSION_NAME_LENGTH} characters`)
    .regex(SESSION_NAME_PATTERN, "Session name can only contain alphanumeric characters, dashes, and underscores")
    .describe("Unique name for the agent session (alphanumeric, dash, underscore only)"),
  agent_name: z.string()
    .optional()
    .describe("Optional agent definition to use (e.g., 'system-architect', 'code-reviewer')"),
  project_dir: ProjectDirSchema,
  prompt: z.string()
    .min(1, "Prompt cannot be empty")
    .describe("Initial prompt or task description for the agent session"),
  async: z.boolean()
    .optional()
    .default(false)
    .describe("Run agent in background (fire-and-forget mode). When true, returns immediately with session info. Use get_agent_status to poll for completion.")
}).strict();

export type StartAgentInput = z.infer<typeof StartAgentInputSchema>;

// Schema for resume_agent tool
export const ResumeAgentInputSchema = z.object({
  session_name: z.string()
    .min(1, "Session name cannot be empty")
    .max(MAX_SESSION_NAME_LENGTH, `Session name must not exceed ${MAX_SESSION_NAME_LENGTH} characters`)
    .regex(SESSION_NAME_PATTERN, "Session name can only contain alphanumeric characters, dashes, and underscores")
    .describe("Name of the existing session to resume"),
  project_dir: ProjectDirSchema,
  prompt: z.string()
    .min(1, "Prompt cannot be empty")
    .describe("Continuation prompt or task description for the resumed session"),
  async: z.boolean()
    .optional()
    .default(false)
    .describe("Run agent in background (fire-and-forget mode). When true, returns immediately with session info. Use get_agent_status to poll for completion.")
}).strict();

export type ResumeAgentInput = z.infer<typeof ResumeAgentInputSchema>;

// Schema for clean_sessions tool
export const CleanSessionsInputSchema = z.object({
  project_dir: ProjectDirSchema
}).strict();

export type CleanSessionsInput = z.infer<typeof CleanSessionsInputSchema>;

// Schema for get_agent_status tool
export const GetAgentStatusInputSchema = z.object({
  session_name: z.string()
    .min(1, "Session name cannot be empty")
    .max(MAX_SESSION_NAME_LENGTH, `Session name must not exceed ${MAX_SESSION_NAME_LENGTH} characters`)
    .regex(SESSION_NAME_PATTERN, "Session name can only contain alphanumeric characters, dashes, and underscores")
    .describe("Name of the session to check status for"),
  project_dir: ProjectDirSchema,
  wait_seconds: z.number()
    .min(0, "Wait time must be non-negative")
    .max(300, "Wait time cannot exceed 300 seconds (5 minutes)")
    .optional()
    .default(0)
    .describe("Number of seconds to wait before checking status (default: 0). Useful for polling long-running agents with longer intervals to reduce token usage.")
}).strict();

export type GetAgentStatusInput = z.infer<typeof GetAgentStatusInputSchema>;

// Schema for get_agent_result tool
export const GetAgentResultInputSchema = z.object({
  session_name: z.string()
    .min(1, "Session name cannot be empty")
    .max(MAX_SESSION_NAME_LENGTH, `Session name must not exceed ${MAX_SESSION_NAME_LENGTH} characters`)
    .regex(SESSION_NAME_PATTERN, "Session name can only contain alphanumeric characters, dashes, and underscores")
    .describe("Name of the session to retrieve result from"),
  project_dir: ProjectDirSchema
}).strict();

export type GetAgentResultInput = z.infer<typeof GetAgentResultInputSchema>;