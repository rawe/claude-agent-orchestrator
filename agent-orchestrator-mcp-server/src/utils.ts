/**
 * Shared utility functions for Agent Orchestrator MCP Server
 */

import { spawn } from "child_process";
import {
  AgentInfo,
  SessionInfo,
  ServerConfig,
  ScriptExecutionResult,
  ResponseFormat
} from "./types.js";
import { CHARACTER_LIMIT } from "./constants.js";
import { logger } from "./logger.js";

/**
 * Execute the agent-orchestrator.sh script with given arguments
 */
export async function executeScript(
  config: ServerConfig,
  args: string[],
  stdinInput?: string
): Promise<ScriptExecutionResult> {
  const startTime = Date.now();

  logger.debug("Executing script", {
    scriptPath: config.scriptPath,
    args,
    hasStdin: !!stdinInput,
    stdinLength: stdinInput?.length || 0,
    env: {
      PATH: process.env.PATH,
      HOME: process.env.HOME,
      PWD: process.env.PWD,
      AGENT_ORCHESTRATOR_SCRIPT_PATH: process.env.AGENT_ORCHESTRATOR_SCRIPT_PATH,
      AGENT_ORCHESTRATOR_PROJECT_DIR: process.env.AGENT_ORCHESTRATOR_PROJECT_DIR,
    }
  });

  return new Promise((resolve, reject) => {
    const childProcess = spawn(config.scriptPath, args, {
      env: { ...process.env },
      stdio: ["pipe", "pipe", "pipe"]
    });

    let stdout = "";
    let stderr = "";

    childProcess.stdout?.on("data", (data: Buffer) => {
      const chunk = data.toString();
      stdout += chunk;
      logger.debug("Script stdout chunk", { length: chunk.length });
    });

    childProcess.stderr?.on("data", (data: Buffer) => {
      const chunk = data.toString();
      stderr += chunk;
      logger.debug("Script stderr chunk", { length: chunk.length, content: chunk.substring(0, 200) });
    });

    childProcess.on("error", (error: Error) => {
      logger.error("Script execution error", {
        error: error.message,
        stack: error.stack,
        duration: Date.now() - startTime
      });
      reject(new Error(`Failed to execute script: ${error.message}`));
    });

    childProcess.on("close", (code: number | null) => {
      const duration = Date.now() - startTime;
      const result = {
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        exitCode: code ?? 1
      };

      logger.debug("Script execution completed", {
        exitCode: code,
        stdoutLength: result.stdout.length,
        stderrLength: result.stderr.length,
        duration,
        stdoutPreview: result.stdout.substring(0, 500),
        stderrPreview: result.stderr.substring(0, 500)
      });

      resolve(result);
    });

    // Write stdin input if provided, otherwise close stdin immediately
    if (stdinInput && childProcess.stdin) {
      logger.debug("Writing to script stdin", { length: stdinInput.length });
      childProcess.stdin.write(stdinInput);
      childProcess.stdin.end();
    } else if (childProcess.stdin) {
      // Close stdin immediately if no input to prevent script from waiting
      logger.debug("Closing stdin (no input provided)");
      childProcess.stdin.end();
    }
  });
}

/**
 * Parse agent list output from the list-agents command
 * Format:
 * agent-name:
 * description
 *
 * ---
 *
 * next-agent:
 * description
 */
export function parseAgentList(output: string): AgentInfo[] {
  if (output === "No agent definitions found") {
    return [];
  }

  const agents: AgentInfo[] = [];
  const sections = output.split(/\n---\n/).map(s => s.trim()).filter(s => s.length > 0);

  for (const section of sections) {
    const lines = section.split("\n").filter(line => line.trim().length > 0);
    if (lines.length >= 2) {
      // First line is "name:"
      const nameLine = lines[0];
      const name = nameLine.endsWith(":") ? nameLine.slice(0, -1) : nameLine;

      // Remaining lines are description
      const description = lines.slice(1).join("\n");

      agents.push({ name, description });
    }
  }

  return agents;
}

/**
 * Parse session list output from the list command
 * Format:
 * session-name (session: session-id, project: project-dir)
 */
export function parseSessionList(output: string): SessionInfo[] {
  if (output === "No sessions found") {
    return [];
  }

  const sessions: SessionInfo[] = [];
  const lines = output.split("\n").filter(line => line.trim().length > 0);

  for (const line of lines) {
    // Match pattern: "session-name (session: session-id, project: project-dir)"
    const match = line.match(/^(.+?)\s+\(session:\s+(.+?),\s+project:\s+(.+?)\)$/);
    if (match) {
      sessions.push({
        name: match[1].trim(),
        sessionId: match[2].trim(),
        projectDir: match[3].trim()
      });
    }
  }

  return sessions;
}

/**
 * Format agent list as markdown
 */
export function formatAgentsAsMarkdown(agents: AgentInfo[]): string {
  if (agents.length === 0) {
    return "No agent definitions found";
  }

  const lines: string[] = ["# Available Orchestrated Agents", ""];

  for (const agent of agents) {
    lines.push(`## ${agent.name}`);
    lines.push(agent.description);
    lines.push("");
  }

  return lines.join("\n");
}

/**
 * Format agent list as JSON
 */
export function formatAgentsAsJSON(agents: AgentInfo[]): string {
  const response = {
    total: agents.length,
    agents: agents.map(a => ({
      name: a.name,
      description: a.description
    }))
  };

  return JSON.stringify(response, null, 2);
}

/**
 * Format session list as markdown
 */
export function formatSessionsAsMarkdown(sessions: SessionInfo[]): string {
  if (sessions.length === 0) {
    return "No sessions found";
  }

  const lines: string[] = ["# Agent Sessions", ""];
  lines.push(`Found ${sessions.length} session(s)`);
  lines.push("");

  for (const session of sessions) {
    lines.push(`## ${session.name}`);
    lines.push(`- **Session ID**: ${session.sessionId}`);
    lines.push(`- **Project Directory**: ${session.projectDir}`);
    lines.push("");
  }

  return lines.join("\n");
}

/**
 * Format session list as JSON
 */
export function formatSessionsAsJSON(sessions: SessionInfo[]): string {
  const response = {
    total: sessions.length,
    sessions: sessions.map(s => ({
      name: s.name,
      session_id: s.sessionId,
      project_dir: s.projectDir
    }))
  };

  return JSON.stringify(response, null, 2);
}

/**
 * Handle script execution errors
 */
export function handleScriptError(result: ScriptExecutionResult): string {
  if (result.exitCode !== 0) {
    // Extract error message from stderr
    const errorMessage = result.stderr || result.stdout || "Unknown error occurred";

    // Clean up the error message (remove ANSI color codes if present)
    const cleanError = errorMessage.replace(/\x1b\[[0-9;]*m/g, "");

    return `Error executing agent-orchestrator script: ${cleanError}`;
  }

  return result.stdout;
}

/**
 * Truncate response if it exceeds character limit
 */
export function truncateResponse(text: string): { text: string; truncated: boolean } {
  if (text.length <= CHARACTER_LIMIT) {
    return { text, truncated: false };
  }

  const truncatedText = text.substring(0, CHARACTER_LIMIT) +
    "\n\n[Response truncated due to length. The output exceeded the maximum character limit.]";

  return { text: truncatedText, truncated: true };
}

/**
 * Format tool response based on requested format
 */
export function formatToolResponse(
  data: unknown,
  format: ResponseFormat,
  markdownFormatter: (data: any) => string,
  jsonFormatter: (data: any) => string
): string {
  if (format === ResponseFormat.MARKDOWN) {
    return markdownFormatter(data);
  } else {
    return jsonFormatter(data);
  }
}