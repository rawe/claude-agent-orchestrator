/**
 * TypeScript type definitions for Agent Orchestrator MCP Server
 */

export interface AgentInfo {
  name: string;
  description: string;
}

export interface SessionInfo {
  name: string;
  sessionId: string;
}

export interface ServerConfig {
  scriptPath: string;
}

export enum ResponseFormat {
  MARKDOWN = "markdown",
  JSON = "json"
}

export interface ScriptExecutionResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}