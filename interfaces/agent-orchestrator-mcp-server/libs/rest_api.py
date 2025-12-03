"""
REST API for Agent Orchestrator

Provides a RESTful HTTP interface to the Agent Orchestrator MCP tools.
Uses FastAPI for automatic OpenAPI documentation generation.

Endpoints:
    GET  /api/blueprints          - List available agent blueprints
    GET  /api/sessions            - List all agent sessions
    POST /api/sessions            - Start a new agent session
    POST /api/sessions/{name}/resume - Resume an existing session
    GET  /api/sessions/{name}/status - Get session status
    GET  /api/sessions/{name}/result - Get session result
    DELETE /api/sessions          - Delete all sessions
"""

import json
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from constants import MAX_SESSION_NAME_LENGTH


# Request/Response Models for API documentation
class BlueprintInfo(BaseModel):
    """Agent blueprint information"""

    name: str = Field(description="Blueprint identifier")
    description: str = Field(description="Blueprint capabilities description")


class BlueprintsResponse(BaseModel):
    """Response containing list of agent blueprints"""

    total: int = Field(description="Total number of blueprints")
    blueprints: list[BlueprintInfo] = Field(description="List of available blueprints")


class SessionInfo(BaseModel):
    """Agent session information"""

    name: str = Field(description="Session name")
    session_id: str = Field(description="Session ID or 'initializing'/'unknown'")
    project_dir: str = Field(description="Project directory path")


class SessionsResponse(BaseModel):
    """Response containing list of agent sessions"""

    total: int = Field(description="Total number of sessions")
    sessions: list[SessionInfo] = Field(description="List of sessions")


class StartSessionRequest(BaseModel):
    """Request to start a new agent session"""

    session_name: str = Field(
        min_length=1,
        max_length=MAX_SESSION_NAME_LENGTH,
        description="Unique session identifier (alphanumeric, dash, underscore)",
    )
    prompt: str = Field(min_length=1, description="Initial task prompt for the agent")
    agent_blueprint_name: Optional[str] = Field(
        default=None, description="Blueprint to use (optional)"
    )
    project_dir: Optional[str] = Field(
        default=None, description="Absolute path to project directory (optional)"
    )
    async_mode: bool = Field(
        default=False, description="Run in background and return immediately"
    )


class ResumeSessionRequest(BaseModel):
    """Request to resume an existing session"""

    prompt: str = Field(min_length=1, description="Continuation prompt")
    async_mode: bool = Field(
        default=False, description="Run in background and return immediately"
    )


class SessionStatusResponse(BaseModel):
    """Session status response"""

    status: Literal["running", "finished", "not_existent"] = Field(
        description="Current session status"
    )


class AsyncSessionResponse(BaseModel):
    """Response when session is started in async mode"""

    session_name: str = Field(description="Session name")
    status: str = Field(description="Session status")
    message: str = Field(description="Status message")


class SessionResultResponse(BaseModel):
    """Response containing session result"""

    result: str = Field(description="Agent session output/result")


class DeleteSessionsResponse(BaseModel):
    """Response after deleting sessions"""

    message: str = Field(description="Confirmation message")


class ErrorResponse(BaseModel):
    """Error response"""

    error: str = Field(description="Error message")


def create_api_router(mcp_tools: dict) -> APIRouter:
    """Create FastAPI router with REST endpoints wrapping MCP tools.

    Args:
        mcp_tools: Dictionary containing the MCP tool functions:
            - list_agent_blueprints
            - list_agent_sessions
            - start_agent_session
            - resume_agent_session
            - get_agent_session_status
            - get_agent_session_result
            - delete_all_agent_sessions
    """
    router = APIRouter(prefix="/api", tags=["Agent Orchestrator"])

    @router.get(
        "/blueprints",
        response_model=BlueprintsResponse,
        summary="List agent blueprints",
        description="Get all available agent blueprints that can be used to create sessions",
    )
    async def get_blueprints():
        result = await mcp_tools["list_agent_blueprints"](response_format="json")
        try:
            data = json.loads(result)
            return BlueprintsResponse(
                total=data.get("total", len(data.get("agents", []))),
                blueprints=[
                    BlueprintInfo(name=a["name"], description=a["description"])
                    for a in data.get("agents", [])
                ],
            )
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse blueprint data")

    @router.get(
        "/sessions",
        response_model=SessionsResponse,
        summary="List agent sessions",
        description="Get all agent sessions (running, completed, or initializing)",
    )
    async def get_sessions():
        result = await mcp_tools["list_agent_sessions"](response_format="json")
        try:
            data = json.loads(result)
            return SessionsResponse(
                total=data.get("total", len(data.get("sessions", []))),
                sessions=[
                    SessionInfo(
                        name=s["name"],
                        session_id=s.get("session_id", s.get("sessionId", "unknown")),
                        project_dir=s.get("project_dir", s.get("projectDir", "")),
                    )
                    for s in data.get("sessions", [])
                ],
            )
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse session data")

    @router.post(
        "/sessions",
        response_model=SessionResultResponse | AsyncSessionResponse,
        summary="Start a new agent session",
        description="Create and start a new agent session with the given prompt",
        responses={
            200: {
                "description": "Session result (sync) or session info (async)",
                "content": {
                    "application/json": {
                        "examples": {
                            "sync": {
                                "summary": "Synchronous response",
                                "value": {"result": "Agent output..."},
                            },
                            "async": {
                                "summary": "Asynchronous response",
                                "value": {
                                    "session_name": "my-session",
                                    "status": "running",
                                    "message": "Session started",
                                },
                            },
                        }
                    }
                },
            }
        },
    )
    async def start_session(request: StartSessionRequest):
        result = await mcp_tools["start_agent_session"](
            session_name=request.session_name,
            prompt=request.prompt,
            agent_blueprint_name=request.agent_blueprint_name,
            project_dir=request.project_dir,
            async_mode=request.async_mode,
        )

        if result.startswith("Error:"):
            raise HTTPException(status_code=400, detail=result)

        if request.async_mode:
            try:
                data = json.loads(result)
                return AsyncSessionResponse(**data)
            except json.JSONDecodeError:
                return AsyncSessionResponse(
                    session_name=request.session_name,
                    status="running",
                    message="Session started",
                )
        return SessionResultResponse(result=result)

    @router.post(
        "/sessions/{session_name}/resume",
        response_model=SessionResultResponse | AsyncSessionResponse,
        summary="Resume an agent session",
        description="Continue an existing session with a new prompt",
    )
    async def resume_session(session_name: str, request: ResumeSessionRequest):
        result = await mcp_tools["resume_agent_session"](
            session_name=session_name,
            prompt=request.prompt,
            async_mode=request.async_mode,
        )

        if result.startswith("Error:"):
            raise HTTPException(status_code=400, detail=result)

        if request.async_mode:
            try:
                data = json.loads(result)
                return AsyncSessionResponse(**data)
            except json.JSONDecodeError:
                return AsyncSessionResponse(
                    session_name=session_name,
                    status="running",
                    message="Session resumed",
                )
        return SessionResultResponse(result=result)

    @router.get(
        "/sessions/{session_name}/status",
        response_model=SessionStatusResponse,
        summary="Get session status",
        description="Check the current status of an agent session",
    )
    async def get_session_status(
        session_name: str,
        wait_seconds: int = Query(
            default=0,
            ge=0,
            le=300,
            description="Seconds to wait before checking (for polling)",
        ),
    ):
        result = await mcp_tools["get_agent_session_status"](
            session_name=session_name,
            wait_seconds=wait_seconds,
        )
        try:
            data = json.loads(result)
            return SessionStatusResponse(status=data["status"])
        except (json.JSONDecodeError, KeyError):
            return SessionStatusResponse(status="not_existent")

    @router.get(
        "/sessions/{session_name}/result",
        response_model=SessionResultResponse,
        summary="Get session result",
        description="Retrieve the final output from a completed session",
    )
    async def get_session_result(session_name: str):
        result = await mcp_tools["get_agent_session_result"](session_name=session_name)

        if result.startswith("Error:"):
            raise HTTPException(status_code=400, detail=result)

        return SessionResultResponse(result=result)

    @router.delete(
        "/sessions",
        response_model=DeleteSessionsResponse,
        summary="Delete all sessions",
        description="Permanently delete all agent sessions and their data",
    )
    async def delete_sessions():
        result = await mcp_tools["delete_all_agent_sessions"]()

        if result.startswith("Error:"):
            raise HTTPException(status_code=500, detail=result)

        return DeleteSessionsResponse(message=result)

    return router
