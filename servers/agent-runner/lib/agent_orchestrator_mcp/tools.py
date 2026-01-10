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

        Each blueprint includes:
        - name: Agent identifier
        - description: Human-readable description
        - type: "autonomous" (interprets intent) or "procedural" (follows defined procedure)
        - tags: List of tags for filtering
        - parameters_schema: JSON Schema for parameter validation

        Parameter Requirements by Agent Type:
        - Autonomous agents (type="autonomous"):
          - Always require {"prompt": string} at minimum
          - If parameters_schema is null: accepts only {"prompt": "..."}
          - If parameters_schema is set: accepts additional custom parameters
            (prompt is still required and will be added automatically if not in schema)
          - Additional parameters are formatted and prepended to the prompt

        - Procedural agents (type="procedural"):
          - Use parameters_schema directly (no implicit prompt requirement)
          - Parameters are converted to CLI arguments

        Args:
            ctx: Request context with tags filter

        Returns:
            List of agent blueprint dictionaries with type and schema info
        """
        try:
            agents = await self._client.list_agents(tags=ctx.tags)

            # Return agent info with type and schema
            return [
                {
                    "name": agent.get("name"),
                    "description": agent.get("description", ""),
                    "type": agent.get("type", "autonomous"),
                    "tags": agent.get("tags", []),
                    "parameters_schema": agent.get("parameters_schema"),
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
        parameters: dict,
        agent_name: Optional[str] = None,
        project_dir: Optional[str] = None,
        mode: str = "sync",
    ) -> dict:
        """Start a new agent session.

        Creates a new session and executes it via an available runner.

        Parameter Requirements:
        - For autonomous agents without custom schema: {"prompt": "user message"}
        - For autonomous agents with custom schema: Include all required fields
          from the agent's parameters_schema, plus "prompt" (always required)
        - For procedural agents: Match the agent's parameters_schema exactly

        To check an agent's schema, use list_agent_blueprints() and examine
        the parameters_schema field. If null for autonomous agents, use
        the default {"prompt": "..."} format.

        Args:
            ctx: Request context with parent session ID for callbacks
            parameters: Input parameters - validated against agent's schema
            agent_name: Agent blueprint name (optional)
            project_dir: Optional project directory path
            mode: Execution mode - "sync", "async_poll", or "async_callback"

        Returns:
            For sync mode: {"session_id": "...", "result_text": "...", "result_data": ...}
            For async modes: {"session_id": "...", "status": "pending"}

        Raises:
            ToolError: If session creation or execution fails
        """
        import json as _json
        # Validate parameters size (use JSON length as proxy)
        params_len = len(_json.dumps(parameters))
        if params_len > MAX_PROMPT_LENGTH:
            raise ToolError(
                f"Parameters too large: {params_len} characters (max {MAX_PROMPT_LENGTH})"
            )

        # Parameter validation is now handled by the Coordinator (Phase 3: Schema Validation)
        # The Coordinator validates parameters against the agent's parameters_schema
        # or implicit schema for autonomous agents. See run_queue.py for details.

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
                parameters=parameters,
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
                    # session_result is now {result_text, result_data}
                    result_text = session_result.get("result_text") or ""
                    result_data = session_result.get("result_data")

                    # Truncate result_text if too long
                    if len(result_text) > MAX_RESULT_LENGTH:
                        result_text = (
                            result_text[:MAX_RESULT_LENGTH]
                            + f"\n\n[Result truncated at {MAX_RESULT_LENGTH} characters]"
                        )
                    return {
                        "session_id": session_id,
                        "result_text": result_text,
                        "result_data": result_data,
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
        parameters: dict,
        mode: str = "sync",
    ) -> dict:
        """Resume an existing agent session.

        Continues a previously started session with new input.

        Parameter Requirements (same as start_agent_session):
        - For autonomous agents without custom schema: {"prompt": "user message"}
        - For autonomous agents with custom schema: Include all required fields
          from the agent's parameters_schema, plus "prompt" (always required)
        - For procedural agents: Match the agent's parameters_schema exactly

        Args:
            ctx: Request context with parent session ID for callbacks
            session_id: ID of the session to resume
            parameters: Input parameters - validated against agent's schema
            mode: Execution mode - "sync", "async_poll", or "async_callback"

        Returns:
            For sync mode: {"session_id": "...", "result_text": "...", "result_data": ...}
            For async modes: {"session_id": "...", "status": "pending"}

        Raises:
            ToolError: If session doesn't exist or resume fails
        """
        import json as _json
        # Validate parameters size (use JSON length as proxy)
        params_len = len(_json.dumps(parameters))
        if params_len > MAX_PROMPT_LENGTH:
            raise ToolError(
                f"Parameters too large: {params_len} characters (max {MAX_PROMPT_LENGTH})"
            )

        # Parameter validation is now handled by the Coordinator (Phase 3: Schema Validation)
        # The Coordinator validates parameters against the agent's parameters_schema
        # or implicit schema for autonomous agents. See run_queue.py for details.

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
                parameters=parameters,
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
                    # session_result is now {result_text, result_data}
                    result_text = session_result.get("result_text") or ""
                    result_data = session_result.get("result_data")

                    # Truncate result_text if too long
                    if len(result_text) > MAX_RESULT_LENGTH:
                        result_text = (
                            result_text[:MAX_RESULT_LENGTH]
                            + f"\n\n[Result truncated at {MAX_RESULT_LENGTH} characters]"
                        )
                    return {
                        "session_id": session_id,
                        "result_text": result_text,
                        "result_data": result_data,
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
            {"session_id": "...", "result_text": "...", "result_data": ...}

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
            # result is now {result_text, result_data}
            result_text = result.get("result_text") or ""
            result_data = result.get("result_data")

            # Truncate result_text if too long
            if len(result_text) > MAX_RESULT_LENGTH:
                result_text = (
                    result_text[:MAX_RESULT_LENGTH]
                    + f"\n\n[Result truncated at {MAX_RESULT_LENGTH} characters]"
                )

            return {
                "session_id": session_id,
                "result_text": result_text,
                "result_data": result_data,
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
