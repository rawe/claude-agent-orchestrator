"""
Constants for Agent Orchestrator MCP Server

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

import os

# API Configuration
ENV_API_URL = "AGENT_ORCHESTRATOR_API_URL"
DEFAULT_API_URL = "http://127.0.0.1:8765"


def get_api_url() -> str:
    """Get Agent Coordinator API URL from environment or default."""
    return os.environ.get(ENV_API_URL, DEFAULT_API_URL)


# Character limit for responses
CHARACTER_LIMIT = 25000

# HTTP Header for parent session ID (in HTTP mode) - ADR-010
HEADER_AGENT_SESSION_ID = "X-Agent-Session-Id"

# Environment variable for parent session ID (in stdio mode) - ADR-010
ENV_AGENT_SESSION_ID = "AGENT_SESSION_ID"

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
