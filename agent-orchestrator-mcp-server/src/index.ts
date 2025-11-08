#!/usr/bin/env node
/**
 * Agent Orchestrator MCP Server
 *
 * This MCP server provides tools to orchestrate specialized Claude Code agents
 * through the agent-orchestrator.sh script. It enables:
 * - Listing available agent definitions
 * - Managing agent sessions (create, resume, list, clean)
 * - Executing long-running tasks in specialized agent contexts
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import * as path from "path";
import { fileURLToPath } from "url";
import {
  ListAgentsInputSchema,
  ListSessionsInputSchema,
  StartAgentInputSchema,
  ResumeAgentInputSchema,
  CleanSessionsInputSchema,
  type ListAgentsInput,
  type ListSessionsInput,
  type StartAgentInput,
  type ResumeAgentInput,
  type CleanSessionsInput
} from "./schemas.js";
import {
  executeScript,
  parseAgentList,
  parseSessionList,
  formatAgentsAsMarkdown,
  formatAgentsAsJSON,
  formatSessionsAsMarkdown,
  formatSessionsAsJSON,
  handleScriptError,
  truncateResponse,
  formatToolResponse
} from "./utils.js";
import { ServerConfig, ResponseFormat } from "./types.js";
import { ENV_SCRIPT_PATH } from "./constants.js";
import { logger } from "./logger.js";

// Get configuration from environment variables
function getServerConfig(): ServerConfig {
  const scriptPath = process.env[ENV_SCRIPT_PATH];
  if (!scriptPath) {
    console.error(`ERROR: ${ENV_SCRIPT_PATH} environment variable is required`);
    console.error(`Please set it to the absolute path of agent-orchestrator.sh`);
    process.exit(1);
  }

  return {
    scriptPath: path.resolve(scriptPath)
  };
}

// Create MCP server instance
const server = new McpServer({
  name: "agent-orchestrator-mcp-server",
  version: "1.0.0"
});

// Get server configuration
const config = getServerConfig();

// Register list_agents tool
server.registerTool(
  "list_agents",
  {
    title: "List Available Orchestrated Agents",
    description: `List all available specialized agent definitions that can be used with start_agent.

This tool discovers agent definitions configured in the agent orchestrator system. Each agent provides specialized capabilities (e.g., system architecture, code review, documentation writing) and can be used when starting new agent sessions.

Args:
  - response_format ('markdown' | 'json'): Output format (default: 'markdown')

Returns:
  For JSON format: Structured data with schema:
  {
    "total": number,           // Total number of agents found
    "agents": [
      {
        "name": string,        // Agent name/identifier (e.g., "system-architect")
        "description": string  // Description of agent's capabilities
      }
    ]
  }

  For Markdown format: Human-readable formatted list with agent names and descriptions

Examples:
  - Use when: "What agents are available?" -> Check available specialized agents
  - Use when: "Show me the agent definitions" -> List all agent capabilities
  - Don't use when: You want to see running sessions (use list_sessions instead)

Error Handling:
  - Returns "No agent definitions found" if no agents are configured
  - Returns error message if script execution fails`,
    inputSchema: ListAgentsInputSchema.shape,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false
    }
  },
  async (params: ListAgentsInput) => {
    try {
      // Execute list-agents command
      const result = await executeScript(config, ["list-agents"]);

      if (result.exitCode !== 0) {
        const errorMsg = handleScriptError(result);
        return {
          content: [{
            type: "text",
            text: errorMsg
          }],
          isError: true
        };
      }

      // Parse the agent list
      const agents = parseAgentList(result.stdout);

      // Format based on requested format
      const formattedResponse = formatToolResponse(
        agents,
        params.response_format,
        formatAgentsAsMarkdown,
        formatAgentsAsJSON
      );

      // Check character limit
      const { text, truncated } = truncateResponse(formattedResponse);

      return {
        content: [{
          type: "text",
          text: text
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Register list_sessions tool
server.registerTool(
  "list_sessions",
  {
    title: "List All Agent Sessions",
    description: `List all existing agent sessions with their session IDs.

This tool shows all agent sessions that have been created, including their names and session IDs. Sessions can be in various states (running, completed, or initializing).

Args:
  - response_format ('markdown' | 'json'): Output format (default: 'markdown')

Returns:
  For JSON format: Structured data with schema:
  {
    "total": number,              // Total number of sessions
    "sessions": [
      {
        "name": string,           // Session name (e.g., "architect")
        "session_id": string      // Session ID or status ("initializing", "unknown")
      }
    ]
  }

  For Markdown format: Human-readable formatted list with session names and IDs

Session ID values:
  - UUID string: Normal session ID (e.g., "3db5dca9-6829-4cb7-a645-c64dbd98244d")
  - "initializing": Session file exists but hasn't started yet
  - "unknown": Session ID couldn't be extracted

Examples:
  - Use when: "What sessions exist?" -> See all created sessions
  - Use when: "Show me my agent sessions" -> List all sessions with their IDs
  - Don't use when: You want to see available agent types (use list_agents instead)

Error Handling:
  - Returns "No sessions found" if no sessions exist
  - Returns error message if script execution fails`,
    inputSchema: ListSessionsInputSchema.shape,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false
    }
  },
  async (params: ListSessionsInput) => {
    try {
      // Execute list command
      const result = await executeScript(config, ["list"]);

      if (result.exitCode !== 0) {
        const errorMsg = handleScriptError(result);
        return {
          content: [{
            type: "text",
            text: errorMsg
          }],
          isError: true
        };
      }

      // Parse the session list
      const sessions = parseSessionList(result.stdout);

      // Format based on requested format
      const formattedResponse = formatToolResponse(
        sessions,
        params.response_format,
        formatSessionsAsMarkdown,
        formatSessionsAsJSON
      );

      // Check character limit
      const { text, truncated } = truncateResponse(formattedResponse);

      return {
        content: [{
          type: "text",
          text: text
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Register start_agent tool
server.registerTool(
  "start_agent",
  {
    title: "Start New Orchestrated Agent Session",
    description: `Start a new orchestrated agent session with an optional specialized agent definition.

This tool creates a new agent session that runs in a separate Claude Code context. Sessions can be generic (no agent) or specialized (with an agent definition). The agent will execute the provided prompt and return the result.

IMPORTANT: This operation may take significant time to complete as it runs a full Claude Code session. The agent will process the prompt and may use multiple tool calls to complete the task.

Args:
  - session_name (string): Unique identifier for the session (alphanumeric, dash, underscore; max 60 chars)
  - agent_name (string, optional): Name of agent definition to use (e.g., "system-architect", "code-reviewer")
  - prompt (string): Initial task description or prompt for the agent

Session naming rules:
  - Must be unique (cannot already exist)
  - 1-60 characters
  - Only alphanumeric, dash (-), and underscore (_) allowed
  - Use descriptive names (e.g., "architect", "reviewer", "dev-agent")

Returns:
  The result/output from the completed agent session. This is the agent's final response after processing the prompt and completing all necessary tasks.

Examples:
  - Use when: "Create an architecture design" -> Start session with system-architect agent
  - Use when: "Analyze this codebase" -> Start generic session or use code-reviewer agent
  - Don't use when: Session already exists (use resume_agent instead)
  - Don't use when: You just want to list available agents (use list_agents instead)

Error Handling:
  - "Session already exists" -> Use resume_agent or choose different name
  - "Session name too long" -> Use shorter name (max 60 characters)
  - "Invalid characters" -> Only use alphanumeric, dash, underscore
  - "Agent not found" -> Check available agents with list_agents
  - "No prompt provided" -> Provide a prompt argument`,
    inputSchema: StartAgentInputSchema.shape,
    annotations: {
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: true
    }
  },
  async (params: StartAgentInput) => {
    logger.info("start_agent called", {
      session_name: params.session_name,
      agent_name: params.agent_name,
      prompt_length: params.prompt?.length || 0
    });

    try {
      // Build command arguments
      const args = ["new", params.session_name];

      // Add agent if specified
      if (params.agent_name) {
        args.push("--agent", params.agent_name);
      }

      // Add prompt
      args.push("-p", params.prompt);

      logger.debug("start_agent: executing script", { args });

      // Execute new command
      const result = await executeScript(config, args);

      if (result.exitCode !== 0) {
        logger.error("start_agent: script failed", {
          exitCode: result.exitCode,
          stdout: result.stdout,
          stderr: result.stderr
        });

        const errorMsg = handleScriptError(result);
        return {
          content: [{
            type: "text",
            text: errorMsg
          }],
          isError: true
        };
      }

      logger.info("start_agent: script succeeded", {
        stdoutLength: result.stdout.length,
        stderrLength: result.stderr.length
      });

      // Check character limit
      const { text, truncated } = truncateResponse(result.stdout);

      if (truncated) {
        logger.warn("start_agent: response truncated", {
          originalLength: result.stdout.length,
          truncatedLength: text.length
        });
      }

      return {
        content: [{
          type: "text",
          text: text
        }]
      };
    } catch (error) {
      logger.error("start_agent: exception", {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined
      });

      return {
        content: [{
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Register resume_agent tool
server.registerTool(
  "resume_agent",
  {
    title: "Resume Existing Orchestrated Agent Session",
    description: `Resume an existing agent session with a new prompt to continue the work.

This tool continues an existing agent session, allowing you to build upon previous work. The agent remembers all context from previous interactions in this session. Any agent association from session creation is automatically maintained.

IMPORTANT: This operation may take significant time to complete as it runs a full Claude Code session. The agent will process the new prompt in the context of all previous interactions.

Args:
  - session_name (string): Name of the existing session to resume
  - prompt (string): Continuation prompt or new task description

Returns:
  The result/output from the resumed agent session. This is the agent's response after processing the new prompt in context of previous interactions.

Examples:
  - Use when: "Continue the architecture work" -> Resume existing architect session
  - Use when: "Add security considerations" -> Resume session to build on previous work
  - Use when: "Review the changes made" -> Resume to get status or make adjustments
  - Don't use when: Session doesn't exist (use start_agent to create it)
  - Don't use when: Starting fresh work (use start_agent for new sessions)

Error Handling:
  - "Session does not exist" -> Use start_agent to create a new session
  - "Session name invalid" -> Check session name format
  - "No prompt provided" -> Provide a prompt argument

Note: The agent definition used during session creation is automatically remembered and applied when resuming.`,
    inputSchema: ResumeAgentInputSchema.shape,
    annotations: {
      readOnlyHint: false,
      destructiveHint: false,
      idempotentHint: false,
      openWorldHint: true
    }
  },
  async (params: ResumeAgentInput) => {
    try {
      // Build command arguments
      const args = ["resume", params.session_name, "-p", params.prompt];

      // Execute resume command
      const result = await executeScript(config, args);

      if (result.exitCode !== 0) {
        const errorMsg = handleScriptError(result);
        return {
          content: [{
            type: "text",
            text: errorMsg
          }],
          isError: true
        };
      }

      // Check character limit
      const { text, truncated } = truncateResponse(result.stdout);

      return {
        content: [{
          type: "text",
          text: text
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Register clean_sessions tool
server.registerTool(
  "clean_sessions",
  {
    title: "Clean All Agent Sessions",
    description: `Remove all agent sessions and their associated data.

This tool permanently deletes all agent sessions, including their conversation history and metadata. This operation cannot be undone.

WARNING: This is a destructive operation. All session data will be permanently lost.

Args:
  None

Returns:
  Confirmation message indicating sessions were removed or that no sessions existed.

Examples:
  - Use when: "Clear all sessions" -> Remove all session data
  - Use when: "Start fresh" -> Delete all existing sessions
  - Use when: "Clean up old sessions" -> Remove all sessions to free up space
  - Don't use when: You only want to remove specific sessions (currently not supported)
  - Don't use when: You might want to resume sessions later

Error Handling:
  - "No sessions to remove" -> No sessions exist (safe to ignore)
  - Returns error message if script execution fails

Note: This operation is idempotent - running it multiple times has the same effect as running it once.`,
    inputSchema: CleanSessionsInputSchema.shape,
    annotations: {
      readOnlyHint: false,
      destructiveHint: true,
      idempotentHint: true,
      openWorldHint: false
    }
  },
  async (params: CleanSessionsInput) => {
    try {
      // Execute clean command
      const result = await executeScript(config, ["clean"]);

      if (result.exitCode !== 0) {
        const errorMsg = handleScriptError(result);
        return {
          content: [{
            type: "text",
            text: errorMsg
          }],
          isError: true
        };
      }

      return {
        content: [{
          type: "text",
          text: result.stdout
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Main function
async function main() {
  logger.info("Agent Orchestrator MCP Server starting", {
    scriptPath: config.scriptPath,
    cwd: process.cwd(),
    nodeVersion: process.version,
    env: {
      AGENT_ORCHESTRATOR_SCRIPT_PATH: process.env.AGENT_ORCHESTRATOR_SCRIPT_PATH,
      AGENT_ORCHESTRATOR_PROJECT_DIR: process.env.AGENT_ORCHESTRATOR_PROJECT_DIR,
      PATH: process.env.PATH
    }
  });

  console.error("Agent Orchestrator MCP Server");
  console.error(`Script path: ${config.scriptPath}`);
  console.error("");

  // Create transport
  const transport = new StdioServerTransport();

  // Connect server to transport
  await server.connect(transport);

  logger.info("Agent Orchestrator MCP server connected and running");
  console.error("Agent Orchestrator MCP server running via stdio");
}

// Run the server
main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
