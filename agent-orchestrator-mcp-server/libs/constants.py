"""
Constants for Agent Orchestrator MCP Server
"""

# Environment variable names
ENV_COMMAND_PATH = "AGENT_ORCHESTRATOR_COMMAND_PATH"

# Session name constraints
MAX_SESSION_NAME_LENGTH = 60
SESSION_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"

# Character limit for responses
CHARACTER_LIMIT = 25000

# Internal command names (used as keys to map to Python CLI commands)
CMD_START_SESSION = "start-session"
CMD_RESUME_SESSION = "resume-session"
CMD_LIST_SESSIONS = "list-sessions"
CMD_LIST_DEFINITIONS = "list-definitions"
CMD_DELETE_ALL_SESSIONS = "delete-all-sessions"
CMD_GET_STATUS = "get-status"
CMD_GET_RESULT = "get-result"
