"""
Executor Invocation Payload

Handles parsing and validation of JSON payloads for the unified ao-*-exec entrypoint.
Replaces individual CLI arguments with a structured, versioned schema.

Schema version: 2.0

Runner resolves blueprint and placeholders before spawning executor.
Executor receives fully resolved agent_blueprint.

Note: Uses session_id (coordinator-generated) per ADR-010.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Any
import json
import sys
import logging

logger = logging.getLogger(__name__)

# Current schema version - used by both runner (to build) and executor (to validate)
SCHEMA_VERSION = "2.0"

# Supported schema versions
SUPPORTED_VERSIONS = {SCHEMA_VERSION}

# JSON Schema for documentation and --schema flag
INVOCATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ExecutorInvocation",
    "description": "Schema 2.0 - Executor receives resolved agent_blueprint",
    "type": "object",
    "required": ["schema_version", "mode", "session_id", "prompt"],
    "properties": {
        "schema_version": {
            "type": "string",
            "const": "2.0",
            "description": "Schema version",
        },
        "mode": {
            "type": "string",
            "enum": ["start", "resume"],
            "description": "Execution mode",
        },
        "session_id": {
            "type": "string",
            "minLength": 1,
            "description": "Coordinator-generated session identifier (ADR-010)",
        },
        "prompt": {
            "type": "string",
            "description": "User input text (may be long)",
        },
        "project_dir": {
            "type": "string",
            "description": "Working directory path (start mode only)",
        },
        "agent_blueprint": {
            "type": "object",
            "description": "Fully resolved agent blueprint with placeholders replaced",
            "properties": {
                "name": {"type": "string"},
                "system_prompt": {"type": "string"},
                "mcp_servers": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "url": {"type": "string"},
                            "headers": {"type": "object"},
                        },
                    },
                },
            },
        },
        "metadata": {
            "type": "object",
            "additionalProperties": True,
            "description": "Extensible metadata",
        },
    },
}


@dataclass
class ExecutorInvocation:
    """
    Structured payload for ao-*-exec unified executor.

    The agent_blueprint contains the fully resolved blueprint
    (with placeholders like ${AGENT_ORCHESTRATOR_MCP_URL} replaced).

    Attributes:
        schema_version: Schema version for forward compatibility
        mode: Execution mode ('start' or 'resume')
        session_id: Coordinator-generated session identifier (ADR-010)
        prompt: User input text
        project_dir: Working directory path (start mode only)
        agent_blueprint: Fully resolved agent blueprint
        metadata: Extensible key-value map for future use
    """

    schema_version: str
    mode: Literal["start", "resume"]
    session_id: str
    prompt: str
    project_dir: Optional[str] = None
    agent_blueprint: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_stdin(cls) -> "ExecutorInvocation":
        """
        Parse invocation from stdin JSON.

        Reads JSON from stdin, validates required fields and schema version,
        and returns an ExecutorInvocation instance.

        Returns:
            ExecutorInvocation instance

        Raises:
            ValueError: If stdin is empty, JSON is invalid, or validation fails
        """
        raw = sys.stdin.read()
        return cls.from_json(raw)

    @classmethod
    def from_json(cls, raw: str) -> "ExecutorInvocation":
        """
        Parse invocation from JSON string.

        Args:
            raw: JSON string to parse

        Returns:
            ExecutorInvocation instance

        Raises:
            ValueError: If JSON is empty, invalid, or validation fails
        """
        if not raw.strip():
            raise ValueError("No input received on stdin")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Validate required fields
        required_fields = ("schema_version", "mode", "session_id", "prompt")
        for f in required_fields:
            if f not in data:
                raise ValueError(f"Missing required field: {f}")

        # Validate schema version
        if data["schema_version"] not in SUPPORTED_VERSIONS:
            supported = ", ".join(sorted(SUPPORTED_VERSIONS))
            raise ValueError(
                f"Unsupported schema version: {data['schema_version']}. "
                f"Supported: {supported}"
            )

        # Validate mode
        if data["mode"] not in ("start", "resume"):
            raise ValueError(
                f"Invalid mode: {data['mode']}. Must be 'start' or 'resume'"
            )

        # Warn about ignored fields in resume mode
        if data["mode"] == "resume":
            if data.get("project_dir"):
                logger.warning("Field 'project_dir' ignored in resume mode")

        # Warn about unknown fields (forward compatibility)
        known_fields = {
            "schema_version",
            "mode",
            "session_id",
            "prompt",
            "project_dir",
            "agent_blueprint",
            "metadata",
        }
        for key in data.keys():
            if key not in known_fields:
                logger.warning(f"Unknown field '{key}' ignored")

        return cls(
            schema_version=data["schema_version"],
            mode=data["mode"],
            session_id=data["session_id"],
            prompt=data["prompt"],
            project_dir=data.get("project_dir"),
            agent_blueprint=data.get("agent_blueprint"),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "session_id": self.session_id,
            "prompt": self.prompt,
        }
        if self.agent_blueprint:
            d["agent_blueprint"] = self.agent_blueprint
        if self.project_dir:
            d["project_dir"] = self.project_dir
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    def log_summary(self) -> None:
        """
        Log invocation summary without sensitive data.

        Logs schema version, mode, session ID, and prompt length
        (not the actual prompt content for security).
        """
        if self.agent_blueprint:
            agent_info = f"blueprint={self.agent_blueprint.get('name', 'unnamed')}"
        else:
            agent_info = "no_agent"

        logger.info(
            f"Invocation: version={self.schema_version} mode={self.mode} "
            f"session={self.session_id} {agent_info} prompt_len={len(self.prompt)}"
        )
