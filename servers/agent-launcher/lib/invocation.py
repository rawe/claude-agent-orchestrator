"""
Executor Invocation Payload

Handles parsing and validation of JSON payloads for the unified ao-exec entrypoint.
Replaces individual CLI arguments with a structured, versioned schema.

Schema version: 1.0
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Any
import json
import sys
import logging

logger = logging.getLogger(__name__)

# Current schema version - used by both launcher (to build) and executor (to validate)
SCHEMA_VERSION = "1.0"

# Supported schema versions for backward compatibility
SUPPORTED_VERSIONS = {SCHEMA_VERSION}

# JSON Schema for documentation and --schema flag
INVOCATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ExecutorInvocation",
    "description": "Payload schema for ao-exec unified executor",
    "type": "object",
    "required": ["schema_version", "mode", "session_name", "prompt"],
    "properties": {
        "schema_version": {
            "type": "string",
            "pattern": "^[0-9]+\\.[0-9]+$",
            "description": "Schema version (semver major.minor)",
        },
        "mode": {
            "type": "string",
            "enum": ["start", "resume"],
            "description": "Execution mode",
        },
        "session_name": {
            "type": "string",
            "minLength": 1,
            "description": "Unique session identifier",
        },
        "prompt": {
            "type": "string",
            "description": "User input text (may be long)",
        },
        "agent_name": {
            "type": "string",
            "description": "Agent blueprint name (start mode only)",
        },
        "project_dir": {
            "type": "string",
            "description": "Working directory path (start mode only)",
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
    Structured payload for ao-exec unified executor.

    Attributes:
        schema_version: Schema version for forward compatibility
        mode: Execution mode ('start' or 'resume')
        session_name: Unique session identifier
        prompt: User input text
        agent_name: Agent blueprint name (start mode only)
        project_dir: Working directory path (start mode only)
        metadata: Extensible key-value map for future use
    """

    schema_version: str
    mode: Literal["start", "resume"]
    session_name: str
    prompt: str
    agent_name: Optional[str] = None
    project_dir: Optional[str] = None
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
        required_fields = ("schema_version", "mode", "session_name", "prompt")
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
            for ignored in ("agent_name", "project_dir"):
                if data.get(ignored):
                    logger.warning(f"Field '{ignored}' ignored in resume mode")

        # Warn about unknown fields (forward compatibility)
        known_fields = {
            "schema_version",
            "mode",
            "session_name",
            "prompt",
            "agent_name",
            "project_dir",
            "metadata",
        }
        for key in data.keys():
            if key not in known_fields:
                logger.warning(f"Unknown field '{key}' ignored")

        return cls(
            schema_version=data["schema_version"],
            mode=data["mode"],
            session_name=data["session_name"],
            prompt=data["prompt"],
            agent_name=data.get("agent_name"),
            project_dir=data.get("project_dir"),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "session_name": self.session_name,
            "prompt": self.prompt,
        }
        if self.agent_name:
            d["agent_name"] = self.agent_name
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

        Logs schema version, mode, session name, and prompt length
        (not the actual prompt content for security).
        """
        logger.info(
            f"Invocation: version={self.schema_version} mode={self.mode} "
            f"session={self.session_name} prompt_len={len(self.prompt)}"
        )
