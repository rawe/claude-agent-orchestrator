"""
Type definitions for Agent Orchestrator MCP Server
"""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class ResponseFormat(str, Enum):
    """Response format options"""
    MARKDOWN = "markdown"
    JSON = "json"


class AgentInfo(BaseModel):
    """Information about an agent definition"""
    name: str = Field(description="Agent name/identifier")
    description: str = Field(description="Agent capabilities description")


class SessionInfo(BaseModel):
    """Information about an agent session"""
    name: str = Field(description="Session name")
    sessionId: str = Field(description="Session ID or status", alias="session_id")
    projectDir: str = Field(description="Project directory path", alias="project_dir")

    class Config:
        populate_by_name = True


class ServerConfig(BaseModel):
    """Server configuration"""
    commandPath: str = Field(description="Path to commands directory", alias="command_path")

    class Config:
        populate_by_name = True


class ScriptExecutionResult(BaseModel):
    """Result of script execution"""
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    exitCode: int = Field(description="Exit code", alias="exit_code")

    class Config:
        populate_by_name = True


class AsyncExecutionResult(BaseModel):
    """Result of async script execution"""
    session_name: str = Field(description="Session name")
    status: Literal["running"] = Field(default="running", description="Execution status")
    message: str = Field(description="Status message")
