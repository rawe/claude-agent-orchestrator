"""
Session Management

Handles session creation, validation, state detection, and operations.
"""

from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re


SessionState = Literal["running", "finished", "not_existent"]


@dataclass
class SessionMetadata:
    """Metadata stored in {session_name}.meta.json"""

    session_name: str
    session_id: str  # Claude session ID from SDK
    agent: Optional[str]
    project_dir: Path
    agents_dir: Path
    created_at: datetime
    last_resumed_at: datetime
    schema_version: str = "1.0"


def validate_session_name(name: str) -> None:
    """
    Validate session name format.

    Rules (MUST MATCH BASH):
    - Not empty
    - Max 60 characters
    - Only alphanumeric, dash, underscore: ^[a-zA-Z0-9_-]+$

    Raises:
        ValueError: With descriptive message matching bash script errors
    """
    if not name:
        raise ValueError("Session name cannot be empty")

    if len(name) > 60:
        raise ValueError(f"Session name too long (max 60 characters, got {len(name)})")

    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(
            "Session name can only contain alphanumeric characters, dashes, and underscores"
        )


def get_session_status(session_name: str, sessions_dir: Path) -> SessionState:
    """
    Detect session state (MUST MATCH BASH EXACTLY).

    Algorithm (from bash cmd_status):
    1. Check if .meta.json exists → if not: return "not_existent"
    2. Check if .jsonl exists → if not: return "running" (initializing)
    3. Check if .jsonl is empty (size == 0) → if empty: return "running"
    4. Read last line of .jsonl:
       - If has "type": "result" field: return "finished"
       - Else: return "running"
    5. On any error (JSON parse, file read): return "running"

    Returns:
        - "not_existent": Session doesn't exist
        - "running": Session in progress
        - "finished": Session completed
    """
    meta_file = sessions_dir / f"{session_name}.meta.json"
    session_file = sessions_dir / f"{session_name}.jsonl"

    # Step 1: Check meta file exists
    if not meta_file.exists():
        return "not_existent"

    # Step 2-3: Check session file exists and is not empty
    if not session_file.exists() or session_file.stat().st_size == 0:
        return "running"

    # Step 4: Read last line and check for result type
    try:
        # Efficiently read last line of potentially large file
        with open(session_file, "rb") as f:
            # Handle edge case: file with single line
            try:
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b"\n":
                    f.seek(-2, os.SEEK_CUR)
            except OSError:
                # File too small, seek to beginning
                f.seek(0)

            last_line = f.readline().decode("utf-8")

        last_msg = json.loads(last_line)
        if last_msg.get("type") == "result":
            return "finished"
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        # On any error, assume running
        pass

    return "running"


def save_session_metadata(
    session_name: str,
    agent: Optional[str],
    project_dir: Path,
    agents_dir: Path,
    sessions_dir: Path,
    session_id: Optional[str] = None,
) -> None:
    """
    Create .meta.json file for new session.

    STAGE 1 (ao-new): Called without session_id before Claude runs.
    STAGE 2 (ao-new): session_id added later via update_session_id().

    Args:
        session_name: Name of the session
        agent: Agent name (optional)
        project_dir: Project directory path
        agents_dir: Agents directory path
        sessions_dir: Sessions directory path
        session_id: Claude session ID (optional, added in Stage 2)

    Implementation:
    1. Create metadata dict with all required fields
    2. Ensure sessions directory exists
    3. Write to {sessions_dir}/{session_name}.meta.json
    """
    # Ensure sessions directory exists
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Create metadata dict
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        "session_name": session_name,
        "agent": agent,  # Can be null
        "project_dir": str(project_dir.resolve()),
        "agents_dir": str(agents_dir.resolve()),
        "created_at": now,
        "last_resumed_at": now,
        "schema_version": "1.0",
    }

    # Add session_id only if provided (Stage 2)
    if session_id is not None:
        metadata["session_id"] = session_id

    # Write to file
    meta_file = sessions_dir / f"{session_name}.meta.json"
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")  # Add trailing newline for consistency


def update_session_id(
    session_name: str, session_id: str, sessions_dir: Path
) -> None:
    """
    Update metadata file with session_id (STAGE 2).

    Called during Claude session streaming when session_id is first received.
    This allows the session to be resumable even while still running.

    Args:
        session_name: Name of the session
        session_id: Claude session ID from SDK
        sessions_dir: Sessions directory path

    Raises:
        FileNotFoundError: If metadata file doesn't exist
        json.JSONDecodeError: If invalid JSON in metadata file
    """
    meta_file = sessions_dir / f"{session_name}.meta.json"

    # Read existing metadata
    if not meta_file.exists():
        raise FileNotFoundError(
            f"Metadata file not found for session '{session_name}'. "
            "Stage 1 metadata should be created before calling update_session_id()."
        )

    with open(meta_file, "r") as f:
        metadata = json.load(f)

    # Update session_id field
    metadata["session_id"] = session_id

    # Write back to file
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")


def load_session_metadata(session_name: str, sessions_dir: Path) -> SessionMetadata:
    """
    Load metadata from .meta.json file.

    Returns:
        SessionMetadata with all fields populated

    Raises:
        FileNotFoundError: If meta.json doesn't exist
        json.JSONDecodeError: If invalid JSON
        KeyError: If required fields missing (including session_id)
    """
    # Build path and check exists
    meta_file = sessions_dir / f"{session_name}.meta.json"
    if not meta_file.exists():
        raise FileNotFoundError(f"Session metadata not found: {meta_file}")

    # Read and parse JSON
    with open(meta_file, "r") as f:
        data = json.load(f)

    # Parse datetimes (strip trailing Z for ISO format)
    created_at = datetime.fromisoformat(data["created_at"].rstrip("Z"))
    last_resumed_at = datetime.fromisoformat(data["last_resumed_at"].rstrip("Z"))

    # Return SessionMetadata
    return SessionMetadata(
        session_name=data["session_name"],
        session_id=data["session_id"],  # Required field
        agent=data.get("agent"),  # Can be null
        project_dir=Path(data["project_dir"]),
        agents_dir=Path(data["agents_dir"]),
        created_at=created_at,
        last_resumed_at=last_resumed_at,
        schema_version=data.get("schema_version", "legacy"),
    )


def update_session_metadata(session_name: str, sessions_dir: Path) -> None:
    """
    Update last_resumed_at timestamp.

    Implementation:
    1. Load existing metadata JSON
    2. Update last_resumed_at timestamp
    3. Write back to file atomically (using temp file)
    """
    meta_file = sessions_dir / f"{session_name}.meta.json"

    # Load existing metadata
    with open(meta_file, "r") as f:
        data = json.load(f)

    # Update timestamp
    data["last_resumed_at"] = datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )

    # Write atomically using temp file
    tmp_file = sessions_dir / f"{session_name}.meta.json.tmp"
    with open(tmp_file, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    # Rename temp to original (atomic on POSIX systems)
    os.replace(tmp_file, meta_file)


def extract_session_id(session_name: str, sessions_dir: Path) -> str:
    """
    Extract Claude session_id from .meta.json file.

    NOTE: Since we're using the SDK (not CLI), session_id is now stored
    in .meta.json, not in the first line of .jsonl file.

    Returns:
        Session ID string

    Raises:
        FileNotFoundError: If meta.json doesn't exist
        json.JSONDecodeError: If invalid JSON
        KeyError: If session_id field missing
    """
    metadata = load_session_metadata(session_name, sessions_dir)
    return metadata.session_id


def extract_result(session_file: Path) -> str:
    """
    Extract result from last line of .jsonl file.

    NOTE: Our simplified JSONL format stores result in last line with type="result".

    Returns:
        Result string from completed session

    Raises:
        FileNotFoundError: If session file doesn't exist
        json.JSONDecodeError: If last line isn't valid JSON
        ValueError: If result field missing or session not finished
    """
    if not session_file.exists():
        raise FileNotFoundError(f"Session file not found: {session_file}")

    if session_file.stat().st_size == 0:
        raise ValueError("Session file is empty")

    # Read last line efficiently (same method as get_session_status)
    try:
        with open(session_file, "rb") as f:
            # Handle edge case: file with single line
            try:
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b"\n":
                    f.seek(-2, os.SEEK_CUR)
            except OSError:
                # File too small, seek to beginning
                f.seek(0)

            last_line = f.readline().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"Failed to read session file: {e}")

    # Parse JSON
    try:
        last_msg = json.loads(last_line)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Last line is not valid JSON: {e}", last_line, 0)

    # Extract result
    result = last_msg.get("result")
    if not result:
        raise ValueError("No result found in last line (session may not be finished)")

    return result


def list_all_sessions(sessions_dir: Path) -> list[tuple[str, str, str]]:
    """
    List all sessions with basic info.

    NOTE: Session ID now comes from .meta.json, not .jsonl file.

    Returns:
        List of (session_name, session_id, project_dir) tuples
    """
    # Ensure sessions_dir exists
    if not sessions_dir.exists():
        return []

    sessions = []

    # Find all .meta.json files
    for meta_file in sessions_dir.glob("*.meta.json"):
        # Extract session name (remove .meta.json suffix)
        session_name = meta_file.stem.replace(".meta", "")

        # Try to load metadata
        try:
            metadata = load_session_metadata(session_name, sessions_dir)
            session_id = metadata.session_id
            project_dir = str(metadata.project_dir)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            # If error, use fallback values
            session_id = "unknown"
            project_dir = "unknown"

        sessions.append((session_name, session_id, project_dir))

    return sessions
