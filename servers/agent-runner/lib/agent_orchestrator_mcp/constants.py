"""
Constants for the Agent Orchestrator MCP Server.

Defines HTTP header names, character limits, and other configuration values.
"""

# HTTP Header names for context extraction
HEADER_SESSION_ID = "X-Agent-Session-Id"
HEADER_AGENT_TAGS = "X-Agent-Tags"
HEADER_ADDITIONAL_DEMANDS = "X-Additional-Demands"

# Character limits
MAX_PROMPT_LENGTH = 100_000  # 100k characters for prompts
MAX_RESULT_LENGTH = 50_000   # 50k characters for result summaries

# Default polling values for sync mode
DEFAULT_POLL_INTERVAL = 2.0  # seconds
DEFAULT_SYNC_TIMEOUT = 600.0  # 10 minutes

# Default port (0 means dynamic assignment)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 0
