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
  GetAgentStatusInputSchema,
  GetAgentResultInputSchema,
  type ListAgentsInput,
  type ListSessionsInput,
  type StartAgentInput,
  type ResumeAgentInput,
  type CleanSessionsInput,
  type GetAgentStatusInput,
  type GetAgentResultInput
} from "./schemas.js";
import {
  executeScript,
  executeScriptAsync,
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
import { ENV_COMMAND_PATH } from "./constants.js";
import { logger } from "./logger.js";

// Get configuration from environment variables
function getServerConfig(): ServerConfig {
  const commandPath = process.env[ENV_COMMAND_PATH];
  if (!commandPath) {
    console.error(`ERROR: ${ENV_COMMAND_PATH} environment variable is required`);
    console.error(`Please set it to the absolute path of the commands directory`);
    process.exit(1);
  }

  // Normalize path: remove trailing slash if present
  const normalizedPath = commandPath.replace(/\/$/, '');

  return {
    commandPath: path.resolve(normalizedPath)
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
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
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
    logger.info("list_agents called", {
      project_dir: params.project_dir,
      response_format: params.response_format
    });

    try {
      // Build command arguments - command name must be first
      const args = ["list-agents"];

      // Add project_dir if specified (supersedes environment variable)
      if (params.project_dir) {
        args.push("--project-dir", params.project_dir);
      }

      logger.debug("list_agents: executing script", { args });

      // Execute list-agents command
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
    description: `List all existing agent sessions with their session IDs and project directories.

This tool shows all agent sessions that have been created, including their names, session IDs, and the project directory used for each session. Sessions can be in various states (running, completed, or initializing).

Args:
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
  - response_format ('markdown' | 'json'): Output format (default: 'markdown')

Returns:
  For JSON format: Structured data with schema:
  {
    "total": number,              // Total number of sessions
    "sessions": [
      {
        "name": string,           // Session name (e.g., "architect")
        "session_id": string,     // Session ID or status ("initializing", "unknown")
        "project_dir": string     // Project directory path used for this session
      }
    ]
  }

  For Markdown format: Human-readable formatted list with session names, IDs, and project directories

Session ID values:
  - UUID string: Normal session ID (e.g., "3db5dca9-6829-4cb7-a645-c64dbd98244d")
  - "initializing": Session file exists but hasn't started yet
  - "unknown": Session ID couldn't be extracted

Project Directory values:
  - Absolute path: The project directory used when the session was created
  - "unknown": Project directory couldn't be extracted (legacy sessions)

Examples:
  - Use when: "What sessions exist?" -> See all created sessions
  - Use when: "Show me my agent sessions" -> List all sessions with their IDs and project directories
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
    logger.info("list_sessions called", {
      project_dir: params.project_dir,
      response_format: params.response_format
    });

    try {
      // Build command arguments - command name must be first
      const args = ["list"];

      // Add project_dir if specified (supersedes environment variable)
      if (params.project_dir) {
        args.push("--project-dir", params.project_dir);
      }

      logger.debug("list_sessions: executing script", { args });

      // Execute list command
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
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
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
      project_dir: params.project_dir,
      prompt_length: params.prompt?.length || 0,
      async: params.async
    });

    try {
      // Build command arguments
      const args = ["new", params.session_name];

      // Add project_dir if specified (supersedes environment variable)
      if (params.project_dir) {
        args.push("--project-dir", params.project_dir);
      }

      // Add agent if specified
      if (params.agent_name) {
        args.push("--agent", params.agent_name);
      }

      // Add prompt
      args.push("-p", params.prompt);

      logger.debug("start_agent: executing script", { args, async: params.async });

      // Check if async mode requested
      if (params.async === true) {
        logger.info("start_agent: using async execution (fire-and-forget mode)");

        // Execute in background (detached mode)
        const asyncResult = await executeScriptAsync(config, args);

        logger.info("start_agent: async process spawned", {
          session_name: asyncResult.session_name
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              session_name: asyncResult.session_name,
              status: asyncResult.status,
              message: asyncResult.message
            }, null, 2)
          }]
        };
      }

      // Original blocking behavior (async=false or undefined)
      logger.info("start_agent: using synchronous execution (blocking mode)");
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
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!
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
    logger.info("resume_agent called", {
      session_name: params.session_name,
      project_dir: params.project_dir,
      prompt_length: params.prompt?.length || 0,
      async: params.async
    });

    try {
      // Build command arguments
      const args = ["resume", params.session_name];

      // Add project_dir if specified (supersedes environment variable)
      if (params.project_dir) {
        args.push("--project-dir", params.project_dir);
      }

      // Add prompt
      args.push("-p", params.prompt);

      logger.debug("resume_agent: executing script", { args, async: params.async });

      // Check if async mode requested
      if (params.async === true) {
        logger.info("resume_agent: using async execution (fire-and-forget mode)");

        // Execute in background (detached mode)
        const asyncResult = await executeScriptAsync(config, args);

        logger.info("resume_agent: async process spawned", {
          session_name: asyncResult.session_name
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              session_name: asyncResult.session_name,
              status: asyncResult.status,
              message: asyncResult.message
            }, null, 2)
          }]
        };
      }

      // Original blocking behavior (async=false or undefined)
      logger.info("resume_agent: using synchronous execution (blocking mode)");
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
  - project_dir (string, optional): Project directory path (must be absolute path). Only set when instructed to set a project dir!

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
    logger.info("clean_sessions called", {
      project_dir: params.project_dir
    });

    try {
      // Build command arguments - command name must be first
      const args = ["clean"];

      // Add project_dir if specified (supersedes environment variable)
      if (params.project_dir) {
        args.push("--project-dir", params.project_dir);
      }

      logger.debug("clean_sessions: executing script", { args });

      // Execute clean command
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

// Register get_agent_status tool
server.registerTool(
  "get_agent_status",
  {
    title: "Get Agent Session Status",
    description: `Check the current status of an agent session.

Returns one of three statuses:
- "running": Session is currently executing or initializing
- "finished": Session completed successfully with a result
- "not_existent": Session does not exist

Use this tool to poll for completion when using async mode with start_agent or resume_agent.

Args:
  - session_name (string): Name of the session to check
  - project_dir (string, optional): Project directory path
  - wait_seconds (number, optional): Seconds to wait before checking status (default: 0, max: 300)

Returns:
  JSON object with status field: {"status": "running"|"finished"|"not_existent"}

Examples:
  - Poll until finished: Keep calling until status="finished"
  - Poll with interval: Use wait_seconds=10 to wait 10 seconds before checking (reduces token usage)
  - Check before resume: Verify session exists before resuming
  - Monitor background execution: Track progress of async agents

Polling Strategy:
  - Short tasks: Poll every 2-5 seconds (wait_seconds=2-5)
  - Long tasks: Poll every 10-30 seconds (wait_seconds=10-30)
  - Very long tasks: Poll every 60+ seconds (wait_seconds=60+)
  - Using wait_seconds reduces token usage by spacing out status checks`,
    inputSchema: GetAgentStatusInputSchema.shape,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false
    }
  },
  async (params: GetAgentStatusInput) => {
    logger.info("get_agent_status called", {
      session_name: params.session_name,
      wait_seconds: params.wait_seconds
    });

    try {
      // Wait if wait_seconds is specified and > 0
      if (params.wait_seconds && params.wait_seconds > 0) {
        logger.debug("get_agent_status: waiting before status check", {
          wait_seconds: params.wait_seconds
        });
        await new Promise(resolve => setTimeout(resolve, params.wait_seconds * 1000));
        logger.debug("get_agent_status: wait completed, checking status now");
      }

      const args = ["status", params.session_name];

      if (params.project_dir) {
        args.push("--project-dir", params.project_dir);
      }

      const result = await executeScript(config, args);

      if (result.exitCode !== 0) {
        // Handle error - likely means session not found or other issue
        return {
          content: [{
            type: "text",
            text: JSON.stringify({ status: "not_existent" }, null, 2)
          }]
        };
      }

      // Parse status from stdout (should be one of: running, finished, not_existent)
      const status = result.stdout.trim();

      return {
        content: [{
          type: "text",
          text: JSON.stringify({ status }, null, 2)
        }]
      };
    } catch (error) {
      // Handle exceptions
      logger.error("get_agent_status: exception", { error });
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ status: "not_existent" }, null, 2)
        }]
      };
    }
  }
);

// Register get_agent_result tool
server.registerTool(
  "get_agent_result",
  {
    title: "Get Agent Session Result",
    description: `Retrieve the final result from a completed agent session.

This tool extracts the result from a session that has finished executing. It will fail with an error if the session is still running or does not exist.

Workflow:
  1. Start agent with async=true
  2. Poll with get_agent_status until status="finished"
  3. Call get_agent_result to retrieve the final output

Args:
  - session_name (string): Name of the completed session
  - project_dir (string, optional): Project directory path

Returns:
  The agent's final response/result as text

Error Handling:
  - "Session still running" -> Poll get_agent_status until finished
  - "Session not found" -> Verify session name is correct
  - "No result found" -> Session may have failed, check status`,
    inputSchema: GetAgentResultInputSchema.shape,
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      idempotentHint: true,
      openWorldHint: false
    }
  },
  async (params: GetAgentResultInput) => {
    logger.info("get_agent_result called", { session_name: params.session_name });

    try {
      // First check status to provide helpful error messages
      const statusArgs = ["status", params.session_name];
      if (params.project_dir) {
        statusArgs.push("--project-dir", params.project_dir);
      }

      const statusResult = await executeScript(config, statusArgs);
      const status = statusResult.stdout.trim();

      if (status === "not_existent") {
        return {
          content: [{
            type: "text",
            text: `Error: Session '${params.session_name}' does not exist. Please check the session name.`
          }],
          isError: true
        };
      }

      if (status === "running") {
        return {
          content: [{
            type: "text",
            text: `Error: Session '${params.session_name}' is still running. Use get_agent_status to poll until status is 'finished'.`
          }],
          isError: true
        };
      }

      // Session is finished, retrieve result
      const args = ["get-result", params.session_name];
      if (params.project_dir) {
        args.push("--project-dir", params.project_dir);
      }

      const result = await executeScript(config, args);

      if (result.exitCode !== 0) {
        logger.error("get_agent_result: script failed", {
          exitCode: result.exitCode,
          stderr: result.stderr
        });

        return {
          content: [{
            type: "text",
            text: `Error retrieving result: ${result.stderr || 'Unknown error'}`
          }],
          isError: true
        };
      }

      // Check character limit
      const { text, truncated } = truncateResponse(result.stdout);

      if (truncated) {
        logger.warn("get_agent_result: response truncated", {
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
      logger.error("get_agent_result: exception", { error });
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
    commandPath: config.commandPath,
    cwd: process.cwd(),
    nodeVersion: process.version,
    env: {
      AGENT_ORCHESTRATOR_COMMAND_PATH: process.env.AGENT_ORCHESTRATOR_COMMAND_PATH,
      AGENT_ORCHESTRATOR_PROJECT_DIR: process.env.AGENT_ORCHESTRATOR_PROJECT_DIR,
      PATH: process.env.PATH
    }
  });

  console.error("Agent Orchestrator MCP Server");
  console.error(`Commands path: ${config.commandPath}`);
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
