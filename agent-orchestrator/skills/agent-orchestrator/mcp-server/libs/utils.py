"""
Shared utility functions for Agent Orchestrator MCP Server
"""

import asyncio
import json
import os
import re
import subprocess
from typing import Callable, List, Optional, TypeVar

from constants import (
    CHARACTER_LIMIT,
    CMD_DELETE_ALL_SESSIONS,
    CMD_GET_RESULT,
    CMD_GET_STATUS,
    CMD_LIST_DEFINITIONS,
    CMD_LIST_SESSIONS,
    CMD_RESUME_SESSION,
    CMD_START_SESSION,
)
from logger import logger
from types_models import (
    AgentInfo,
    AsyncExecutionResult,
    ResponseFormat,
    ScriptExecutionResult,
    ServerConfig,
    SessionInfo,
)

T = TypeVar("T")

# Command name mapping from internal command names to Python CLI command files
COMMAND_NAME_MAP = {
    CMD_START_SESSION: "ao-new",
    CMD_RESUME_SESSION: "ao-resume",
    CMD_LIST_SESSIONS: "ao-list-sessions",
    CMD_LIST_DEFINITIONS: "ao-list-agents",
    CMD_DELETE_ALL_SESSIONS: "ao-clean",
    CMD_GET_STATUS: "ao-status",
    CMD_GET_RESULT: "ao-get-result",
}


async def execute_script(
    config: ServerConfig,
    args: List[str],
    stdin_input: Optional[str] = None,
) -> ScriptExecutionResult:
    """
    Execute Python agent orchestrator commands via uv

    Args:
        config: Server configuration
        args: Command arguments (first element is command name)
        stdin_input: Optional stdin input to pass to the process

    Returns:
        ScriptExecutionResult with stdout, stderr, and exit code
    """
    start_time = asyncio.get_event_loop().time()

    # Extract command name (first argument) and remaining args
    if not args:
        raise ValueError("No command specified")

    command_name, *command_args = args

    # Map bash subcommand to Python command name
    python_command = COMMAND_NAME_MAP.get(command_name)
    if not python_command:
        raise ValueError(f"Unknown command: {command_name}")

    # Build full command path
    full_command_path = f"{config.commandPath}/{python_command}"

    # Build uv run arguments: uv run <command-path> <args...>
    uv_args = ["uv", "run", full_command_path] + command_args

    logger.debug(
        "Executing Python command via uv",
        {
            "commandPath": config.commandPath,
            "pythonCommand": python_command,
            "fullCommandPath": full_command_path,
            "uvArgs": uv_args,
            "hasStdin": bool(stdin_input),
            "stdinLength": len(stdin_input) if stdin_input else 0,
            "env": {
                "PATH": os.environ.get("PATH"),
                "HOME": os.environ.get("HOME"),
                "PWD": os.environ.get("PWD"),
                "AGENT_ORCHESTRATOR_COMMAND_PATH": os.environ.get("AGENT_ORCHESTRATOR_COMMAND_PATH"),
                "AGENT_ORCHESTRATOR_PROJECT_DIR": os.environ.get("AGENT_ORCHESTRATOR_PROJECT_DIR"),
            },
        },
    )

    try:
        # Execute via subprocess
        process = await asyncio.create_subprocess_exec(
            *uv_args,
            stdin=subprocess.PIPE if stdin_input else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )

        # Communicate with process
        stdout_bytes, stderr_bytes = await process.communicate(
            input=stdin_input.encode() if stdin_input else None
        )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        exit_code = process.returncode or 0

        duration = asyncio.get_event_loop().time() - start_time

        result = ScriptExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exitCode=exit_code,
        )

        logger.debug(
            "Command execution completed",
            {
                "exitCode": exit_code,
                "stdoutLength": len(stdout),
                "stderrLength": len(stderr),
                "duration": duration,
                "stdoutPreview": stdout[:500] if stdout else "",
                "stderrPreview": stderr[:500] if stderr else "",
            },
        )

        return result

    except Exception as error:
        duration = asyncio.get_event_loop().time() - start_time
        logger.error(
            "Command execution error",
            {
                "error": str(error),
                "duration": duration,
            },
        )
        raise Exception(f"Failed to execute command: {error}")


async def execute_script_async(
    config: ServerConfig,
    args: List[str],
    stdin_input: Optional[str] = None,
) -> AsyncExecutionResult:
    """
    Execute a script command asynchronously (fire-and-forget mode)
    Spawns a detached process that continues running after this function returns

    Args:
        config: Server configuration
        args: Command arguments (first element is command name)
        stdin_input: Optional stdin input to pass to the process

    Returns:
        AsyncExecutionResult with session metadata
    """
    start_time = asyncio.get_event_loop().time()

    # Extract command name and map to Python command
    if not args:
        raise ValueError("No command specified")

    command_name, *command_args = args

    python_command = COMMAND_NAME_MAP.get(command_name)
    if not python_command:
        raise ValueError(f"Unknown command: {command_name}")

    # Build full command path
    full_command_path = f"{config.commandPath}/{python_command}"
    uv_args = ["uv", "run", full_command_path] + command_args

    logger.debug(
        "Executing Python command asynchronously (detached mode)",
        {
            "commandPath": config.commandPath,
            "pythonCommand": python_command,
            "fullCommandPath": full_command_path,
            "uvArgs": uv_args,
            "hasStdin": bool(stdin_input),
            "stdinLength": len(stdin_input) if stdin_input else 0,
        },
    )

    try:
        # Spawn detached process using subprocess.Popen
        # In Python, we use start_new_session=True for detachment
        process = subprocess.Popen(
            uv_args,
            stdin=subprocess.PIPE if stdin_input else subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=os.environ.copy(),
            start_new_session=True,  # KEY: Process runs independently of parent
        )

        logger.info(
            "Detached process spawned",
            {
                "pid": process.pid,
                "command": python_command,
                "args": command_args,
            },
        )

        # Write stdin if provided, then close immediately
        if stdin_input and process.stdin:
            logger.debug("Writing to async command stdin", {"length": len(stdin_input)})
            process.stdin.write(stdin_input.encode())
            process.stdin.close()

        # Extract session_name from command args (first arg after command name)
        session_name = command_args[0] if command_args else "unknown"

        # Return immediately with metadata
        return AsyncExecutionResult(
            session_name=session_name,
            status="running",
            message="Agent started in background. Use get_agent_session_status to poll for completion and get_agent_session_result to retrieve the final result.",
        )

    except Exception as error:
        duration = asyncio.get_event_loop().time() - start_time
        logger.error(
            "Async command spawn error",
            {
                "error": str(error),
                "duration": duration,
            },
        )
        raise Exception(f"Failed to spawn async command: {error}")


def parse_agent_list(output: str) -> List[AgentInfo]:
    """
    Parse agent list output from the list-agents command
    Format:
    agent-name:
    description

    ---

    next-agent:
    description
    """
    if output == "No agent definitions found":
        return []

    agents: List[AgentInfo] = []
    sections = [s.strip() for s in output.split("\n---\n") if s.strip()]

    for section in sections:
        lines = [line for line in section.split("\n") if line.strip()]
        if len(lines) >= 2:
            # First line is "name:"
            name_line = lines[0]
            name = name_line[:-1] if name_line.endswith(":") else name_line

            # Remaining lines are description
            description = "\n".join(lines[1:])

            agents.append(AgentInfo(name=name, description=description))

    return agents


def parse_session_list(output: str) -> List[SessionInfo]:
    """
    Parse session list output from the list command
    Format:
    session-name (session-id: session-id, project-dir: project-dir)
    """
    if output == "No sessions found":
        return []

    sessions: List[SessionInfo] = []
    lines = [line for line in output.split("\n") if line.strip()]

    for line in lines:
        # Match pattern: "session-name (session-id: session-id, project-dir: project-dir)"
        match = re.match(r"^(.+?)\s+\(session-id:\s+(.+?),\s+project-dir:\s+(.+?)\)$", line)
        if match:
            sessions.append(
                SessionInfo(
                    name=match.group(1).strip(),
                    sessionId=match.group(2).strip(),
                    projectDir=match.group(3).strip(),
                )
            )

    return sessions


def format_agents_as_markdown(agents: List[AgentInfo]) -> str:
    """Format agent list as markdown"""
    if not agents:
        return "No agent definitions found"

    lines = ["# Available Orchestrated Agents", ""]

    for agent in agents:
        lines.append(f"## {agent.name}")
        lines.append(agent.description)
        lines.append("")

    return "\n".join(lines)


def format_agents_as_json(agents: List[AgentInfo]) -> str:
    """Format agent list as JSON"""
    response = {
        "total": len(agents),
        "agents": [{"name": a.name, "description": a.description} for a in agents],
    }
    return json.dumps(response, indent=2)


def format_sessions_as_markdown(sessions: List[SessionInfo]) -> str:
    """Format session list as markdown"""
    if not sessions:
        return "No sessions found"

    lines = ["# Agent Sessions", ""]
    lines.append(f"Found {len(sessions)} session(s)")
    lines.append("")

    for session in sessions:
        lines.append(f"## {session.name}")
        lines.append(f"- **Session ID**: {session.sessionId}")
        lines.append(f"- **Project Directory**: {session.projectDir}")
        lines.append("")

    return "\n".join(lines)


def format_sessions_as_json(sessions: List[SessionInfo]) -> str:
    """Format session list as JSON"""
    response = {
        "total": len(sessions),
        "sessions": [
            {
                "name": s.name,
                "session_id": s.sessionId,
                "project_dir": s.projectDir,
            }
            for s in sessions
        ],
    }
    return json.dumps(response, indent=2)


def handle_script_error(result: ScriptExecutionResult) -> str:
    """Handle script execution errors"""
    if result.exitCode != 0:
        # Extract error message from stderr
        error_message = result.stderr or result.stdout or "Unknown error occurred"

        # Clean up the error message (remove ANSI color codes if present)
        clean_error = re.sub(r"\x1b\[[0-9;]*m", "", error_message)

        return f"Error executing agent-orchestrator script: {clean_error}"

    return result.stdout


def truncate_response(text: str) -> tuple[str, bool]:
    """Truncate response if it exceeds character limit"""
    if len(text) <= CHARACTER_LIMIT:
        return text, False

    truncated_text = (
        text[:CHARACTER_LIMIT]
        + "\n\n[Response truncated due to length. The output exceeded the maximum character limit.]"
    )

    return truncated_text, True


def format_tool_response(
    data: T,
    format: ResponseFormat,
    markdown_formatter: Callable[[T], str],
    json_formatter: Callable[[T], str],
) -> str:
    """Format tool response based on requested format"""
    if format == ResponseFormat.MARKDOWN:
        return markdown_formatter(data)
    else:
        return json_formatter(data)
