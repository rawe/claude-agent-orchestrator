"""
Constants for Agent Orchestrator MCP Server
"""

# Environment variable names
ENV_COMMAND_PATH = "AGENT_ORCHESTRATOR_COMMAND_PATH"

# Session name constraints (from agent-orchestrator.sh)
MAX_SESSION_NAME_LENGTH = 60
SESSION_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"

# Character limit for responses
CHARACTER_LIMIT = 25000
