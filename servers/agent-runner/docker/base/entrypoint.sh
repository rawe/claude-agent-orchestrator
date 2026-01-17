#!/bin/bash
set -e

# Agent Runner Entrypoint Script
# Builds CLI arguments from environment variables and starts the agent-runner.

# Build CLI arguments array
CMD_ARGS=()

# Required: Coordinator URL
CMD_ARGS+=("--coordinator-url" "${AGENT_ORCHESTRATOR_API_URL}")

# Required: Project directory
CMD_ARGS+=("--project-dir" "${PROJECT_DIR}")

# Optional: Profile selection
if [ -n "$PROFILE" ]; then
    CMD_ARGS+=("--profile" "${PROFILE}")
fi

# Optional: Runner tags
if [ -n "$RUNNER_TAGS" ]; then
    CMD_ARGS+=("--tags" "${RUNNER_TAGS}")
fi

# Optional: Fixed MCP server port
if [ -n "$MCP_PORT" ]; then
    CMD_ARGS+=("--mcp-port" "${MCP_PORT}")
fi

# Optional: External MCP server URL
if [ -n "$EXTERNAL_MCP_URL" ]; then
    CMD_ARGS+=("--external-mcp-url" "${EXTERNAL_MCP_URL}")
fi

# Optional: Require matching tags
if [ "$REQUIRE_MATCHING_TAGS" = "true" ]; then
    CMD_ARGS+=("--require-matching-tags")
fi

# Optional: Verbose logging
if [ "$VERBOSE" = "true" ]; then
    CMD_ARGS+=("--verbose")
fi

# Change to agent-runner directory and execute
cd /app/servers/agent-runner
exec uv run --script agent-runner "${CMD_ARGS[@]}"
