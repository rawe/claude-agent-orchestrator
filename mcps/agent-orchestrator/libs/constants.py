"""
Constants for Agent Orchestrator MCP Server
"""

import os

# API Configuration
ENV_API_URL = "AGENT_ORCHESTRATOR_API_URL"
DEFAULT_API_URL = "http://127.0.0.1:8765"


def get_api_url() -> str:
    """Get Agent Coordinator API URL from environment or default."""
    return os.environ.get(ENV_API_URL, DEFAULT_API_URL)


# Session name constraints
MAX_SESSION_NAME_LENGTH = 60
SESSION_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"

# Character limit for responses
CHARACTER_LIMIT = 25000

# HTTP Header for parent session (in HTTP mode)
HEADER_AGENT_SESSION_NAME = "X-Agent-Session-Name"

# Environment variable for parent session (in stdio mode)
ENV_AGENT_SESSION_NAME = "AGENT_SESSION_NAME"

# HTTP Header for tag filtering (in HTTP mode)
HEADER_AGENT_TAGS = "X-Agent-Tags"

# Environment variable for tag filtering (in stdio mode)
ENV_AGENT_TAGS = "AGENT_TAGS"

# HTTP Header for additional demands (in HTTP mode) - ADR-011
# Value should be JSON: {"hostname": "...", "project_dir": "...", "executor_type": "...", "tags": [...]}
HEADER_ADDITIONAL_DEMANDS = "X-Additional-Demands"

# Environment variable for additional demands (in stdio mode) - ADR-011
# Value should be JSON: {"hostname": "...", "project_dir": "...", "executor_type": "...", "tags": [...]}
ENV_ADDITIONAL_DEMANDS = "ADDITIONAL_DEMANDS"
