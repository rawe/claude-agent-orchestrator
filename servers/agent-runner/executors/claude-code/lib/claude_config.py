"""
Claude Code Executor Configuration

Claude-specific configuration keys and defaults for the executor.
Distinct from the shared executor_config (project_dir, api_url, logging).
"""

from typing import Optional
from enum import StrEnum


class ClaudeConfigKey(StrEnum):
    """Keys for claude-code executor configuration."""
    PERMISSION_MODE = "permission_mode"
    SETTING_SOURCES = "setting_sources"
    MODEL = "model"


# Default values when executor_config is missing or incomplete
EXECUTOR_CONFIG_DEFAULTS = {
    ClaudeConfigKey.PERMISSION_MODE: "bypassPermissions",
    ClaudeConfigKey.SETTING_SOURCES: ["user", "project", "local"],
    ClaudeConfigKey.MODEL: None,  # None = use SDK default
}


def get_claude_config(executor_config: Optional[dict]) -> dict:
    """
    Extract claude-code specific configuration with defaults.

    Args:
        executor_config: Raw executor_config dict from invocation (may be None)

    Returns:
        Dict with permission_mode, setting_sources, model (with defaults applied)
    """
    config = executor_config or {}
    return {
        ClaudeConfigKey.PERMISSION_MODE: config.get(
            ClaudeConfigKey.PERMISSION_MODE,
            EXECUTOR_CONFIG_DEFAULTS[ClaudeConfigKey.PERMISSION_MODE]
        ),
        ClaudeConfigKey.SETTING_SOURCES: config.get(
            ClaudeConfigKey.SETTING_SOURCES,
            EXECUTOR_CONFIG_DEFAULTS[ClaudeConfigKey.SETTING_SOURCES]
        ),
        ClaudeConfigKey.MODEL: config.get(
            ClaudeConfigKey.MODEL,
            EXECUTOR_CONFIG_DEFAULTS[ClaudeConfigKey.MODEL]
        ),
    }
