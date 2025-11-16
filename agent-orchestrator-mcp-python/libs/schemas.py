"""
Pydantic validation schemas for Agent Orchestrator MCP Server
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from constants import MAX_SESSION_NAME_LENGTH, SESSION_NAME_PATTERN
from types_models import ResponseFormat


# Base schema for response format
class ResponseFormatField(BaseModel):
    """Base class with response format field"""
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


# Base schema for project directory
class ProjectDirField(BaseModel):
    """Base class with project directory field"""
    project_dir: Optional[str] = Field(
        default=None,
        description="Optional project directory path (must be absolute path). Only set when instructed to set a project dir!"
    )


# Schema for list_agents tool
class ListAgentsInput(ResponseFormatField, ProjectDirField):
    """Input schema for list_agents tool"""
    pass


# Schema for list_sessions tool
class ListSessionsInput(ResponseFormatField, ProjectDirField):
    """Input schema for list_sessions tool"""
    pass


# Schema for start_agent tool
class StartAgentInput(ProjectDirField):
    """Input schema for start_agent tool"""
    session_name: str = Field(
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
        description="Unique name for the agent session (alphanumeric, dash, underscore only)"
    )
    agent_name: Optional[str] = Field(
        default=None,
        description="Optional agent definition to use (e.g., 'system-architect', 'code-reviewer')"
    )
    prompt: str = Field(
        min_length=1,
        description="Initial prompt or task description for the agent session"
    )
    async_: bool = Field(
        default=False,
        alias="async",
        description="Run agent in background (fire-and-forget mode). When true, returns immediately with session info. Use get_agent_status to poll for completion."
    )

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not re.match(SESSION_NAME_PATTERN, v):
            raise ValueError("Session name can only contain alphanumeric characters, dashes, and underscores")
        if len(v) > MAX_SESSION_NAME_LENGTH:
            raise ValueError(f"Session name must not exceed {MAX_SESSION_NAME_LENGTH} characters")
        return v

    class Config:
        populate_by_name = True


# Schema for resume_agent tool
class ResumeAgentInput(ProjectDirField):
    """Input schema for resume_agent tool"""
    session_name: str = Field(
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
        description="Name of the existing session to resume"
    )
    prompt: str = Field(
        min_length=1,
        description="Continuation prompt or task description for the resumed session"
    )
    async_: bool = Field(
        default=False,
        alias="async",
        description="Run agent in background (fire-and-forget mode). When true, returns immediately with session info. Use get_agent_status to poll for completion."
    )

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not re.match(SESSION_NAME_PATTERN, v):
            raise ValueError("Session name can only contain alphanumeric characters, dashes, and underscores")
        if len(v) > MAX_SESSION_NAME_LENGTH:
            raise ValueError(f"Session name must not exceed {MAX_SESSION_NAME_LENGTH} characters")
        return v

    class Config:
        populate_by_name = True


# Schema for clean_sessions tool
class CleanSessionsInput(ProjectDirField):
    """Input schema for clean_sessions tool"""
    pass


# Schema for get_agent_status tool
class GetAgentStatusInput(ProjectDirField):
    """Input schema for get_agent_status tool"""
    session_name: str = Field(
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
        description="Name of the session to check status for"
    )
    wait_seconds: int = Field(
        default=0,
        ge=0,
        le=300,
        description="Number of seconds to wait before checking status (default: 0). Useful for polling long-running agents with longer intervals to reduce token usage."
    )

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not re.match(SESSION_NAME_PATTERN, v):
            raise ValueError("Session name can only contain alphanumeric characters, dashes, and underscores")
        if len(v) > MAX_SESSION_NAME_LENGTH:
            raise ValueError(f"Session name must not exceed {MAX_SESSION_NAME_LENGTH} characters")
        return v


# Schema for get_agent_result tool
class GetAgentResultInput(ProjectDirField):
    """Input schema for get_agent_result tool"""
    session_name: str = Field(
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
        description="Name of the session to retrieve result from"
    )

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not re.match(SESSION_NAME_PATTERN, v):
            raise ValueError("Session name can only contain alphanumeric characters, dashes, and underscores")
        if len(v) > MAX_SESSION_NAME_LENGTH:
            raise ValueError(f"Session name must not exceed {MAX_SESSION_NAME_LENGTH} characters")
        return v
