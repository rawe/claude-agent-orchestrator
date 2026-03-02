"""
Test Payload Builders

Functions to generate test payloads for executor integration tests.
All payloads follow schema version 2.2.
"""

import uuid
import tempfile
from pathlib import Path
from typing import Any


# Use a persistent temp directory for tests
_TEST_PROJECT_DIR: Path | None = None


def get_test_project_dir() -> str:
    """Get or create a test project directory that persists across tests."""
    global _TEST_PROJECT_DIR
    if _TEST_PROJECT_DIR is None or not _TEST_PROJECT_DIR.exists():
        _TEST_PROJECT_DIR = Path(tempfile.mkdtemp(prefix="executor-test-"))
    return str(_TEST_PROJECT_DIR)


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"ses_{uuid.uuid4().hex[:12]}"


def minimal_start_payload(
    session_id: str | None = None,
    prompt: str = "Respond with exactly the word 'hello' and nothing else.",
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Minimal valid start payload.

    Args:
        session_id: Session ID (auto-generated if None)
        prompt: User prompt
        project_dir: Working directory (auto-created if None)

    Returns:
        Valid start payload dict
    """
    return {
        "schema_version": "2.2",
        "mode": "start",
        "session_id": session_id or generate_session_id(),
        "parameters": {"prompt": prompt},
        "project_dir": project_dir or get_test_project_dir(),
    }


def start_with_blueprint_payload(
    session_id: str | None = None,
    prompt: str = "Respond with exactly the word 'hello' and nothing else.",
    agent_name: str = "test-agent",
    system_prompt: str | None = None,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Start payload with agent blueprint.

    Args:
        session_id: Session ID (auto-generated if None)
        prompt: User prompt
        agent_name: Agent name in blueprint
        system_prompt: Optional system prompt
        project_dir: Working directory

    Returns:
        Start payload with blueprint
    """
    payload = minimal_start_payload(session_id, prompt, project_dir)

    blueprint: dict[str, Any] = {"name": agent_name}
    if system_prompt:
        blueprint["system_prompt"] = system_prompt

    payload["agent_blueprint"] = blueprint
    return payload


def start_with_mcp_payload(
    session_id: str | None = None,
    prompt: str = "Use the echo tool to say 'test message'. Then respond with 'done'.",
    mcp_url: str = "http://127.0.0.1:9999",
    mcp_server_name: str = "test-mcp",
    agent_name: str = "mcp-test-agent",
    system_prompt: str | None = None,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Start payload with MCP server configured.

    Args:
        session_id: Session ID (auto-generated if None)
        prompt: User prompt (should reference MCP tools)
        mcp_url: MCP server URL
        mcp_server_name: Name for the MCP server
        agent_name: Agent name
        system_prompt: Optional system prompt
        project_dir: Working directory

    Returns:
        Start payload with MCP server
    """
    payload = start_with_blueprint_payload(
        session_id=session_id,
        prompt=prompt,
        agent_name=agent_name,
        system_prompt=system_prompt,
        project_dir=project_dir,
    )

    payload["agent_blueprint"]["mcp_servers"] = {
        mcp_server_name: {"url": mcp_url}
    }

    return payload


def start_with_output_schema_payload(
    session_id: str | None = None,
    prompt: str = "Return a JSON object with a 'name' field set to 'Alice'.",
    output_schema: dict[str, Any] | None = None,
    agent_name: str = "schema-test-agent",
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Start payload with output schema for structured output validation.

    Args:
        session_id: Session ID (auto-generated if None)
        prompt: User prompt (should request JSON output)
        output_schema: JSON Schema for output validation
        agent_name: Agent name
        project_dir: Working directory

    Returns:
        Start payload with output schema
    """
    if output_schema is None:
        output_schema = {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"}
            }
        }

    payload = start_with_blueprint_payload(
        session_id=session_id,
        prompt=prompt,
        agent_name=agent_name,
        project_dir=project_dir,
    )

    payload["agent_blueprint"]["output_schema"] = output_schema

    return payload


def start_with_custom_params_payload(
    session_id: str | None = None,
    parameters: dict[str, Any] | None = None,
    parameters_schema: dict[str, Any] | None = None,
    agent_name: str = "custom-params-agent",
    system_prompt: str = "Process the inputs provided in the <inputs> block.",
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Start payload with custom parameters (ADR-015 Mode B).

    When parameters_schema is present, ALL parameters are formatted
    as an <inputs> XML block.

    Args:
        session_id: Session ID (auto-generated if None)
        parameters: Custom parameters dict
        parameters_schema: JSON Schema for parameters
        agent_name: Agent name
        system_prompt: System prompt
        project_dir: Working directory

    Returns:
        Start payload with custom parameters
    """
    if parameters is None:
        parameters = {
            "topic": "testing",
            "format": "brief",
        }

    if parameters_schema is None:
        parameters_schema = {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "format": {"type": "string"},
            }
        }

    return {
        "schema_version": "2.2",
        "mode": "start",
        "session_id": session_id or generate_session_id(),
        "parameters": parameters,
        "project_dir": project_dir or get_test_project_dir(),
        "agent_blueprint": {
            "name": agent_name,
            "system_prompt": system_prompt,
            "parameters_schema": parameters_schema,
        },
    }


def resume_payload(
    session_id: str,
    prompt: str = "What was the last thing I asked you?",
    agent_blueprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Resume payload for existing session.

    Args:
        session_id: Session ID to resume (required)
        prompt: Resume prompt
        agent_blueprint: Optional blueprint (for MCP servers)

    Returns:
        Resume payload dict
    """
    payload: dict[str, Any] = {
        "schema_version": "2.2",
        "mode": "resume",
        "session_id": session_id,
        "parameters": {"prompt": prompt},
    }

    if agent_blueprint:
        payload["agent_blueprint"] = agent_blueprint

    return payload


def start_with_executor_config_payload(
    session_id: str | None = None,
    prompt: str = "Respond with exactly the word 'hello' and nothing else.",
    permission_mode: str = "bypassPermissions",
    model: str | None = None,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Start payload with executor config.

    Args:
        session_id: Session ID (auto-generated if None)
        prompt: User prompt
        permission_mode: Permission mode for Claude
        model: Model to use (None = SDK default)
        project_dir: Working directory

    Returns:
        Start payload with executor config
    """
    payload = minimal_start_payload(session_id, prompt, project_dir)

    executor_config: dict[str, Any] = {
        "permission_mode": permission_mode,
    }
    if model:
        executor_config["model"] = model

    payload["executor_config"] = executor_config
    return payload


# Deterministic prompts for testing
PROMPTS = {
    "hello": "Respond with exactly the word 'hello' and nothing else.",
    "number": "Respond with exactly the number '42' and nothing else.",
    "json_name": "Return a JSON object with exactly this structure: {\"name\": \"Alice\"}. Output only the JSON, no other text.",
    "echo_tool": "Use the echo tool to send the message 'test123'. After the tool responds, say 'done'.",
    "get_time_tool": "Use the get_time tool to get the current time. Report what time it returned.",
    "add_numbers_tool": "Use the add_numbers tool to add 5 and 3. Tell me the result.",
    "multi_tool": "First use get_time to get the current time. Then use echo to repeat that time. Finally respond with 'completed'.",
    "context_check": "What was the last thing I asked you to do?",
}
