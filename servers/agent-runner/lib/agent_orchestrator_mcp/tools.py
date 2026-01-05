"""
MCP Tool Implementations for Agent Orchestrator.

Provides all 7 MCP tools that are exposed by the embedded MCP server.
Each tool forwards requests to the Agent Coordinator API.

Tools:
1. list_agent_blueprints - List available agent blueprints (filtered by tags)
2. list_agent_sessions - List all sessions
3. start_agent_session - Start a new agent session
4. resume_agent_session - Resume an existing session
5. get_agent_session_status - Get session status
6. get_agent_session_result - Get session result
7. delete_all_agent_sessions - Delete all sessions
"""

import logging
from typing import Optional

from .schemas import ExecutionMode, RequestContext
from .coordinator_client import (
    CoordinatorClient,
    CoordinatorClientError,
    RunTimeoutError,
    RunFailedError,
)
from .constants import MAX_PROMPT_LENGTH, MAX_RESULT_LENGTH

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Error executing an MCP tool."""
    pass


class AgentOrchestratorTools:
    """
    MCP Tool implementations for Agent Orchestrator.

    Each method corresponds to an MCP tool exposed by the server.
    Methods receive a RequestContext with headers extracted from the HTTP request.
    """

    def __init__(self, client: CoordinatorClient):
        """Initialize tools with Coordinator client.

        Args:
            client: CoordinatorClient for API calls
        """
        self._client = client

    async def list_agent_blueprints(
        self,
        ctx: RequestContext,
    ) -> list[dict]:
        """List available agent blueprints.

        Returns active blueprints filtered by the X-Agent-Tags header from the request.
        If no tags header is present, returns all active blueprints.

        Args:
            ctx: Request context with tags filter

        Returns:
            List of agent blueprint dictionaries with name, description, and tags
        """
        try:
            agents = await self._client.list_agents(tags=ctx.tags)

            # Return simplified agent info
            return [
                {
                    "name": agent.get("name"),
                    "description": agent.get("description", ""),
                    "tags": agent.get("tags", []),
                }
                for agent in agents
            ]
        except CoordinatorClientError as e:
            raise ToolError(f"Failed to list blueprints: {e}")

    async def list_agent_sessions(
        self,
        ctx: RequestContext,
    ) -> list[dict]:
        """List all agent sessions.

        Args:
            ctx: Request context (unused currently)

        Returns:
            List of session dictionaries with id, status, agent_name, etc.
        """
        try:
            sessions = await self._client.list_sessions()

            # Return simplified session info
            return [
                {
                    "session_id": session.get("session_id"),
                    "status": session.get("status"),
                    "agent_name": session.get("agent_name"),
                    "created_at": session.get("created_at"),
                    "last_resumed_at": session.get("last_resumed_at"),
                }
                for session in sessions
            ]
        except CoordinatorClientError as e:
            raise ToolError(f"Failed to list sessions: {e}")

    async def start_agent_session(
        self,
        ctx: RequestContext,
        prompt: str,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
        mode: str = "sync",
    ) -> dict:
        """Start a new agent session.

        Creates a new session and executes it via an available runner.

        Args:
            ctx: Request context with parent session ID for callbacks
            prompt: Initial prompt for the session
            agent_name: Agent blueprint name (optional)
            project_dir: Optional project directory path
            mode: Execution mode - "sync", "async_poll", or "async_callback"

        Returns:
            For sync mode: {"session_id": "...", "result": "..."}
            For async modes: {"session_id": "...", "status": "pending"}

        Raises:
            ToolError: If session creation or execution fails
        """
        # Validate prompt length
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise ToolError(
                f"Prompt too long: {len(prompt)} characters (max {MAX_PROMPT_LENGTH})"
            )

        # Parse execution mode
        try:
            exec_mode = ExecutionMode(mode)
        except ValueError:
            raise ToolError(
                f"Invalid mode: {mode}. Must be one of: sync, async_poll, async_callback"
            )

        # Use project_dir from additional demands if not specified
        if not project_dir:
            project_dir = ctx.get_project_dir()

        # Always get parent session ID for hierarchy tracking (ADR-003/ADR-005)
        # Parent context is always propagated, execution_mode controls callback behavior
        parent_session_id = ctx.parent_session_id

        # For async_callback, parent_session_id is required
        if exec_mode == ExecutionMode.ASYNC_CALLBACK and not parent_session_id:
            raise ToolError(
                "async_callback mode requires X-Agent-Session-Id header"
            )

        try:
            # Create run with execution mode (ADR-003)
            result = await self._client.create_run(
                run_type="start_session",
                prompt=prompt,
                agent_name=agent_name,
                project_dir=project_dir,
                parent_session_id=parent_session_id,
                execution_mode=exec_mode.value,
                additional_demands=ctx.additional_demands or None,
            )

            run_id = result["run_id"]
            session_id = result["session_id"]

            if exec_mode == ExecutionMode.SYNC:
                # Wait for completion
                try:
                    session_result = await self._client.wait_for_run(
                        run_id=run_id,
                        session_id=session_id,
                    )
                    # Truncate result if too long
                    if len(session_result) > MAX_RESULT_LENGTH:
                        session_result = (
                            session_result[:MAX_RESULT_LENGTH]
                            + f"\n\n[Result truncated at {MAX_RESULT_LENGTH} characters]"
                        )
                    return {
                        "session_id": session_id,
                        "result": session_result,
                    }
                except RunTimeoutError as e:
                    raise ToolError(f"Session timed out: {e}")
                except RunFailedError as e:
                    raise ToolError(f"Session failed: {e}")

            else:
                # Async mode - return immediately
                return {
                    "session_id": session_id,
                    "status": "pending",
                }

        except CoordinatorClientError as e:
            raise ToolError(f"Failed to start session: {e}")

    async def resume_agent_session(
        self,
        ctx: RequestContext,
        session_id: str,
        prompt: str,
        mode: str = "sync",
    ) -> dict:
        """Resume an existing agent session.

        Continues a previously started session with a new prompt.

        Args:
            ctx: Request context with parent session ID for callbacks
            session_id: ID of the session to resume
            prompt: Continuation prompt
            mode: Execution mode - "sync", "async_poll", or "async_callback"

        Returns:
            For sync mode: {"session_id": "...", "result": "..."}
            For async modes: {"session_id": "...", "status": "pending"}

        Raises:
            ToolError: If session doesn't exist or resume fails
        """
        # Validate prompt length
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise ToolError(
                f"Prompt too long: {len(prompt)} characters (max {MAX_PROMPT_LENGTH})"
            )

        # Parse execution mode
        try:
            exec_mode = ExecutionMode(mode)
        except ValueError:
            raise ToolError(
                f"Invalid mode: {mode}. Must be one of: sync, async_poll, async_callback"
            )

        # Verify session exists
        session = await self._client.get_session(session_id)
        if not session:
            raise ToolError(f"Session not found: {session_id}")

        # Always get parent session ID for hierarchy tracking (ADR-003/ADR-005)
        # Parent context is always propagated, execution_mode controls callback behavior
        parent_session_id = ctx.parent_session_id

        # For async_callback, parent_session_id is required
        if exec_mode == ExecutionMode.ASYNC_CALLBACK and not parent_session_id:
            raise ToolError(
                "async_callback mode requires X-Agent-Session-Id header"
            )

        try:
            # Create resume run with execution mode (ADR-003)
            result = await self._client.create_run(
                run_type="resume_session",
                session_id=session_id,
                prompt=prompt,
                parent_session_id=parent_session_id,
                execution_mode=exec_mode.value,
                additional_demands=ctx.additional_demands or None,
            )

            run_id = result["run_id"]

            if exec_mode == ExecutionMode.SYNC:
                # Wait for completion
                try:
                    session_result = await self._client.wait_for_run(
                        run_id=run_id,
                        session_id=session_id,
                    )
                    # Truncate result if too long
                    if len(session_result) > MAX_RESULT_LENGTH:
                        session_result = (
                            session_result[:MAX_RESULT_LENGTH]
                            + f"\n\n[Result truncated at {MAX_RESULT_LENGTH} characters]"
                        )
                    return {
                        "session_id": session_id,
                        "result": session_result,
                    }
                except RunTimeoutError as e:
                    raise ToolError(f"Session timed out: {e}")
                except RunFailedError as e:
                    raise ToolError(f"Session failed: {e}")

            else:
                # Async mode - return immediately
                return {
                    "session_id": session_id,
                    "status": "pending",
                }

        except CoordinatorClientError as e:
            raise ToolError(f"Failed to resume session: {e}")

    async def get_agent_session_status(
        self,
        ctx: RequestContext,
        session_id: str,
    ) -> dict:
        """Get the status of an agent session.

        Args:
            ctx: Request context (unused currently)
            session_id: ID of the session

        Returns:
            {"session_id": "...", "status": "running|finished|not_existent"}
        """
        try:
            status = await self._client.get_session_status(session_id)
            return {
                "session_id": session_id,
                "status": status,
            }
        except CoordinatorClientError as e:
            raise ToolError(f"Failed to get status: {e}")

    async def get_agent_session_result(
        self,
        ctx: RequestContext,
        session_id: str,
    ) -> dict:
        """Get the result of a completed agent session.

        Args:
            ctx: Request context (unused currently)
            session_id: ID of the session

        Returns:
            {"session_id": "...", "result": "..."}

        Raises:
            ToolError: If session not found or not finished
        """
        try:
            # Check status first
            status = await self._client.get_session_status(session_id)
            if status == "not_existent":
                raise ToolError(f"Session not found: {session_id}")
            if status != "finished":
                raise ToolError(
                    f"Session not finished: {session_id} (status: {status})"
                )

            result = await self._client.get_session_result(session_id)

            # Truncate if too long
            if len(result) > MAX_RESULT_LENGTH:
                result = (
                    result[:MAX_RESULT_LENGTH]
                    + f"\n\n[Result truncated at {MAX_RESULT_LENGTH} characters]"
                )

            return {
                "session_id": session_id,
                "result": result,
            }
        except CoordinatorClientError as e:
            raise ToolError(f"Failed to get result: {e}")

    async def delete_all_agent_sessions(
        self,
        ctx: RequestContext,
    ) -> dict:
        """Delete all agent sessions.

        Use with caution - this removes all session data.

        Args:
            ctx: Request context (unused currently)

        Returns:
            {"deleted_count": N}
        """
        try:
            deleted = await self._client.delete_all_sessions()
            return {
                "deleted_count": deleted,
            }
        except CoordinatorClientError as e:
            raise ToolError(f"Failed to delete sessions: {e}")
