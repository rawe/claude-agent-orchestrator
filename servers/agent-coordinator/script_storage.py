"""
Script Storage - File I/O operations for script management.

Scripts are stored as directories with the following structure:
    scripts/{name}/
        script.json         # Required: name, description, script_file, parameters_schema, demands
        {script_file}       # The actual script file (e.g., send-notification.py)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from models import (
    RunnerDemands,
    Script,
    ScriptCreate,
    ScriptSummary,
    ScriptUpdate,
)

# Debug logging toggle - matches main.py
DEBUG = os.getenv("DEBUG_LOGGING", "").lower() in ("true", "1", "yes")


def get_scripts_dir() -> Path:
    """
    Get scripts directory.

    Scripts are stored as a sibling to the agents directory:
    - If AGENT_ORCHESTRATOR_AGENTS_DIR is set: {AGENTS_DIR}/../scripts/
    - Otherwise: {PROJECT_DIR}/.agent-orchestrator/scripts/
    """
    agents_dir = os.environ.get("AGENT_ORCHESTRATOR_AGENTS_DIR")
    if agents_dir:
        # Scripts are sibling to agents dir
        path = Path(agents_dir).parent / "scripts"
        if DEBUG:
            print(f"[DEBUG] script_storage: Using {path}", flush=True)
        return path

    # Fall back to project_dir/.agent-orchestrator/scripts
    project_dir = os.environ.get("AGENT_ORCHESTRATOR_PROJECT_DIR", os.getcwd())
    path = Path(project_dir) / ".agent-orchestrator" / "scripts"
    if DEBUG:
        print(
            f"[DEBUG] script_storage: Using {path} (project_dir={project_dir})",
            flush=True,
        )
    return path


def _get_file_times(script_dir: Path) -> tuple[str, str]:
    """Get created_at and modified_at times for script directory."""
    script_json = script_dir / "script.json"
    if script_json.exists():
        stat = script_json.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        return created_at, modified_at
    now = datetime.now().isoformat()
    return now, now


def _read_script_from_dir(script_dir: Path) -> Optional[Script]:
    """Read script data from directory. Returns None if invalid."""
    script_json = script_dir / "script.json"
    if not script_json.exists():
        return None

    try:
        with open(script_json, encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name")
        description = data.get("description")
        script_file = data.get("script_file")
        if not name or not description or not script_file:
            return None

        # Read script file content
        script_file_path = script_dir / script_file
        if not script_file_path.exists():
            return None
        script_content = script_file_path.read_text(encoding="utf-8")

        # Read optional fields
        parameters_schema = data.get("parameters_schema")

        # Read demands
        demands = None
        demands_data = data.get("demands")
        if demands_data:
            demands = RunnerDemands(**demands_data)

        # Get timestamps
        created_at, modified_at = _get_file_times(script_dir)

        return Script(
            name=name,
            description=description,
            script_file=script_file,
            script_content=script_content,
            parameters_schema=parameters_schema,
            demands=demands,
            created_at=created_at,
            modified_at=modified_at,
        )
    except (json.JSONDecodeError, IOError, TypeError):
        return None


def _read_script_summary_from_dir(script_dir: Path) -> Optional[ScriptSummary]:
    """Read script summary from directory. Returns None if invalid."""
    script_json = script_dir / "script.json"
    if not script_json.exists():
        return None

    try:
        with open(script_json, encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name")
        description = data.get("description")
        script_file = data.get("script_file")
        if not name or not description or not script_file:
            return None

        # Check for optional fields
        has_parameters_schema = data.get("parameters_schema") is not None
        demands_data = data.get("demands")
        has_demands = demands_data is not None
        demand_tags = demands_data.get("tags", []) if demands_data else []

        # Get timestamps
        created_at, modified_at = _get_file_times(script_dir)

        return ScriptSummary(
            name=name,
            description=description,
            script_file=script_file,
            has_parameters_schema=has_parameters_schema,
            has_demands=has_demands,
            demand_tags=demand_tags,
            created_at=created_at,
            modified_at=modified_at,
        )
    except (json.JSONDecodeError, IOError, TypeError):
        return None


def list_scripts() -> list[ScriptSummary]:
    """List all valid scripts, sorted by name."""
    scripts_dir = get_scripts_dir()
    if not scripts_dir.exists():
        return []

    scripts = []
    for subdir in scripts_dir.iterdir():
        if not subdir.is_dir():
            continue
        script = _read_script_summary_from_dir(subdir)
        if script:
            scripts.append(script)

    scripts.sort(key=lambda s: s.name)
    return scripts


def get_script(name: str) -> Optional[Script]:
    """Get script by name. Returns None if not found."""
    script_dir = get_scripts_dir() / name
    if not script_dir.is_dir():
        return None
    return _read_script_from_dir(script_dir)


def create_script(data: ScriptCreate) -> Script:
    """
    Create a new script.

    Raises:
        ValueError: If script already exists
    """
    scripts_dir = get_scripts_dir()
    script_dir = scripts_dir / data.name

    if script_dir.exists():
        raise ValueError(f"Script already exists: {data.name}")

    # Create directory
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_dir.mkdir()

    # Write script.json
    script_data: dict[str, Any] = {
        "name": data.name,
        "description": data.description,
        "script_file": data.script_file,
    }
    if data.parameters_schema:
        script_data["parameters_schema"] = data.parameters_schema
    if data.demands:
        script_data["demands"] = data.demands.model_dump(exclude_none=True)

    with open(script_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2)
        f.write("\n")

    # Write script file
    (script_dir / data.script_file).write_text(data.script_content, encoding="utf-8")

    return get_script(data.name)


def update_script(name: str, updates: ScriptUpdate) -> Optional[Script]:
    """
    Update an existing script.

    Returns None if script not found.
    """
    script_dir = get_scripts_dir() / name
    if not script_dir.is_dir():
        return None

    # Read existing script.json
    script_json_path = script_dir / "script.json"
    with open(script_json_path, encoding="utf-8") as f:
        script_data = json.load(f)

    old_script_file = script_data.get("script_file")

    # Apply updates
    if updates.description is not None:
        script_data["description"] = updates.description

    if updates.script_file is not None:
        script_data["script_file"] = updates.script_file

    if updates.parameters_schema is not None:
        if updates.parameters_schema:
            script_data["parameters_schema"] = updates.parameters_schema
        else:
            # Empty dict {} means delete
            script_data.pop("parameters_schema", None)

    if updates.demands is not None:
        if not updates.demands.is_empty():
            script_data["demands"] = updates.demands.model_dump(exclude_none=True)
        else:
            # Empty demands means delete
            script_data.pop("demands", None)

    # Write updated script.json
    with open(script_json_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2)
        f.write("\n")

    # Update script file content if provided
    if updates.script_content is not None:
        new_script_file = updates.script_file or old_script_file
        script_file_path = script_dir / new_script_file

        # If script file name changed, remove old file
        if updates.script_file and old_script_file != updates.script_file:
            old_file_path = script_dir / old_script_file
            if old_file_path.exists():
                old_file_path.unlink()

        script_file_path.write_text(updates.script_content, encoding="utf-8")

    return get_script(name)


def delete_script(name: str) -> bool:
    """Delete a script. Returns True if deleted, False if not found."""
    import shutil

    script_dir = get_scripts_dir() / name
    if not script_dir.is_dir():
        return False

    shutil.rmtree(script_dir)
    return True
