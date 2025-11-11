# Python Agent Orchestrator - Comprehensive Architectural Plan

## Executive Summary

This document provides a detailed architectural plan for rewriting the bash-based agent orchestrator into Python using the Claude Agent SDK. The design maintains 100% compatibility with existing bash sessions while providing a clean, modular Python implementation optimized for LLM workflows through progressive disclosure.

**Key Decision**: Use Claude Agent Python SDK (not CLI subprocess calls) for superior type safety, error handling, and programmatic control.

---

## 1. Overall Architecture Design

### 1.1 Core Principles

1. **Progressive Disclosure**: Each command is a standalone script that imports only what it needs
2. **100% Compatibility**: Must work with sessions created by bash script
3. **Type Safety**: Full type hints throughout
4. **SDK-First**: Use Claude Agent SDK features directly, not CLI subprocess
5. **Centralized Configuration**: Single source of truth for environment variables

### 1.2 Claude SDK Integration Strategy

The SDK will be used for:

- **Session Management**: Create and resume sessions via `query()` function
- **Working Directory Control**: Set `cwd` in `ClaudeAgentOptions`
- **MCP Integration**: Load agent MCP configs and pass to `mcp_servers` parameter
- **Permission Mode**: Set `permission_mode="bypassPermissions"`
- **Stream Handling**: Async iteration over messages, write to `.jsonl` files

Key SDK features NOT used by bash (available for future):
- System prompt injection (we prepend to user prompt instead)
- Custom tool callbacks
- Model selection (uses default)

### 1.3 Module Dependency Graph

```
Command Scripts (commands/)
    ├─> lib/config.py (Environment + CLI args)
    ├─> lib/session.py (State detection, metadata)
    ├─> lib/agent.py (Agent loading)
    ├─> lib/claude_client.py (SDK wrapper)
    └─> lib/utils.py (Common utilities)

lib/claude_client.py
    └─> claude_agent_sdk (External dependency)

lib/agent.py
    └─> lib/config.py (for AGENTS_DIR)

lib/session.py
    └─> lib/config.py (for SESSIONS_DIR)
```

---

## 2. File Structure & Module Organization

### 2.0 Structure Rationale

**Self-contained distribution**: The `commands/` folder contains everything needed - scripts AND their shared library (`lib/` as subdirectory). This design is essential for:

1. **Skills deployment**: Can copy entire `commands/` folder to `.claude/skills/agent-orchestrator/` for Claude Code integration
2. **uv compatibility**: Scripts import from co-located `lib/` using simple relative path: `Path(__file__).parent / "lib"`
3. **Portability**: No external dependencies on sibling directories - commands/ is fully self-contained
4. **PATH simplicity**: `export PATH="$PATH:.../commands"` - single directory to add

**Trade-off accepted**: `lib/` is not at project root, but this enables the self-contained model which is critical for the skills use case.

### 2.1 Directory Layout

```
agent-orchestrator-cli/
├── pyproject.toml              # uv project config
├── README.md
├── docs/
│   ├── architecture.md         # This document
│   ├── development.md
│   └── llm-prompts.md
└── commands/                   # Self-contained commands directory
    ├── ao-new                  # Create new session
    ├── ao-resume               # Resume existing session
    ├── ao-status               # Check session state
    ├── ao-get-result           # Extract result
    ├── ao-list-sessions        # List all sessions
    ├── ao-list-agents          # List available agents
    ├── ao-show-config          # Display session config
    ├── ao-clean                # Remove all sessions
    └── lib/                    # Shared library modules (co-located)
        ├── __init__.py
        ├── config.py           # Configuration management
        ├── session.py          # Session operations
        ├── agent.py            # Agent loading
        ├── claude_client.py    # Claude SDK wrapper
        └── utils.py            # Common utilities
```

### 2.2 Command Scripts Structure

Each script in `commands/` follows this pattern:

```python
#!/usr/bin/env python3
"""
ao-<command> - Brief description

Usage:
    ao-<command> [options] arguments
"""

import sys
from pathlib import Path

# Add lib to path for imports (lib/ is inside commands/)
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from config import load_config
from session import validate_session_name
# ... other minimal imports

def main():
    """Main entry point."""
    # Parse CLI args
    # Load config
    # Execute command
    # Handle errors
    # Print output

if __name__ == "__main__":
    main()
```

---

## 3. Configuration Management

### 3.1 Environment Variables (MUST MATCH BASH)

```python
# lib/config.py - Environment variable names (DO NOT CHANGE)

ENV_PROJECT_DIR = "AGENT_ORCHESTRATOR_PROJECT_DIR"
ENV_SESSIONS_DIR = "AGENT_ORCHESTRATOR_SESSIONS_DIR"
ENV_AGENTS_DIR = "AGENT_ORCHESTRATOR_AGENTS_DIR"
ENV_ENABLE_LOGGING = "AGENT_ORCHESTRATOR_ENABLE_LOGGING"
```

### 3.2 Configuration Precedence

```
1. CLI flags (--project-dir, --sessions-dir, --agents-dir)
2. Environment variables (AGENT_ORCHESTRATOR_*)
3. Default values (PWD-based)
```

### 3.3 Default Paths

```python
# When not overridden:
PROJECT_DIR = Path.cwd()  # Current working directory
SESSIONS_DIR = PROJECT_DIR / ".agent-orchestrator" / "agent-sessions"
AGENTS_DIR = PROJECT_DIR / ".agent-orchestrator" / "agents"
```

### 3.4 Configuration Dataclass

```python
@dataclass
class Config:
    """Global configuration for agent orchestrator."""

    project_dir: Path          # Where Claude executes (cwd)
    sessions_dir: Path         # Where .jsonl and .meta.json files live
    agents_dir: Path           # Where agent definitions are stored
    enable_logging: bool       # Whether to create .log files

    @classmethod
    def from_cli_and_env(
        cls,
        cli_project_dir: Optional[str] = None,
        cli_sessions_dir: Optional[str] = None,
        cli_agents_dir: Optional[str] = None,
    ) -> "Config":
        """
        Load configuration with precedence: CLI > ENV > DEFAULT

        Implementation:
        1. Read environment variables using os.environ.get()
        2. Apply CLI overrides if provided
        3. Resolve all paths to absolute using .resolve()
        4. Validate project_dir exists and is readable
        5. For sessions_dir/agents_dir: find first existing parent, check writable
        6. Return validated Config instance
        """
```

---

## 4. Core Library Modules

### 4.1 lib/config.py

**Purpose**: Centralized configuration loading with precedence handling

**Key Functions**:

```python
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import os


@dataclass
class Config:
    """Configuration with all resolved paths."""
    project_dir: Path
    sessions_dir: Path
    agents_dir: Path
    enable_logging: bool


def load_config(
    cli_project_dir: Optional[str] = None,
    cli_sessions_dir: Optional[str] = None,
    cli_agents_dir: Optional[str] = None,
) -> Config:
    """
    Load configuration with CLI > ENV > DEFAULT precedence.

    Implementation:
    1. Get env values:
       - project = os.environ.get("AGENT_ORCHESTRATOR_PROJECT_DIR")
       - sessions = os.environ.get("AGENT_ORCHESTRATOR_SESSIONS_DIR")
       - agents = os.environ.get("AGENT_ORCHESTRATOR_AGENTS_DIR")
       - logging = os.environ.get("AGENT_ORCHESTRATOR_ENABLE_LOGGING")

    2. Apply precedence for each:
       - Use CLI arg if provided (not None)
       - Else use ENV if set
       - Else use DEFAULT

    3. Resolve paths:
       - Convert strings to Path objects
       - Call .resolve() to make absolute
       - For project_dir: Path.cwd() if not specified
       - For sessions_dir: project_dir / ".agent-orchestrator/agent-sessions"
       - For agents_dir: project_dir / ".agent-orchestrator/agents"

    4. Validate:
       - project_dir must exist and be readable (raise ValueError if not)
       - For sessions_dir/agents_dir: call validate_can_create() helper

    5. Parse logging:
       - Enable if value in ("1", "true", "yes"), case-insensitive

    Returns:
        Config instance with all paths resolved and validated

    Raises:
        ValueError: If project_dir doesn't exist or dirs can't be created
    """


def validate_can_create(path: Path) -> None:
    """
    Validate that a directory can be created.

    Implementation:
    1. If path exists: return (OK)
    2. Find first existing parent: walk up until os.path.exists()
    3. Check parent is writable: os.access(parent, os.W_OK)
    4. If not writable: raise ValueError with descriptive message
    """


def resolve_absolute_path(path_str: str) -> Path:
    """
    Convert path string to absolute Path.

    Implementation:
    1. Create Path object from string
    2. If relative: resolve against Path.cwd()
    3. Call .resolve() to normalize
    4. Return absolute Path
    """
```

**SDK Integration**: None (pure configuration)

**Dependencies**: `os`, `pathlib`, `dataclasses`

---

### 4.2 lib/session.py

**Purpose**: Session lifecycle management, state detection, metadata operations

**Key Functions**:

```python
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass
from datetime import datetime
import json
import os


SessionState = Literal["running", "finished", "not_existent"]


@dataclass
class SessionMetadata:
    """Metadata stored in {session_name}.meta.json"""
    session_name: str
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

    Implementation:
    1. Check if empty: raise ValueError("Session name cannot be empty")
    2. Check length: if len(name) > 60: raise ValueError(f"max 60 chars, got {len}")
    3. Regex check: if not re.match(r'^[a-zA-Z0-9_-]+$', name): raise ValueError

    Raises:
        ValueError: With descriptive message matching bash script errors
    """


def get_session_status(session_name: str, sessions_dir: Path) -> SessionState:
    """
    Detect session state (MUST MATCH BASH EXACTLY).

    Algorithm (from bash cmd_status):
    1. Check if .meta.json exists
       - If not: return "not_existent"
    2. Check if .jsonl exists
       - If not: return "running" (initializing)
    3. Check if .jsonl is empty (size == 0)
       - If empty: return "running"
    4. Read last line of .jsonl:
       - Open file, seek to end, walk backwards to find last newline
       - Parse JSON from last line
       - If has "type": "result" field: return "finished"
       - Else: return "running"
    5. On any error (JSON parse, file read): return "running"

    Implementation:
    meta_file = sessions_dir / f"{session_name}.meta.json"
    session_file = sessions_dir / f"{session_name}.jsonl"

    if not meta_file.exists():
        return "not_existent"

    if not session_file.exists() or session_file.stat().st_size == 0:
        return "running"

    try:
        # Read last line (handle large files efficiently)
        with open(session_file, 'rb') as f:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            last_line = f.readline().decode('utf-8')

        last_msg = json.loads(last_line)
        if last_msg.get('type') == 'result':
            return "finished"
    except:
        pass

    return "running"
    """


def save_session_metadata(
    session_name: str,
    agent: Optional[str],
    project_dir: Path,
    agents_dir: Path,
    sessions_dir: Path,
) -> None:
    """
    Create .meta.json file for new session.

    Implementation:
    1. Create metadata dict:
       {
         "session_name": session_name,
         "agent": agent (or null if None),
         "project_dir": str(project_dir.resolve()),
         "agents_dir": str(agents_dir.resolve()),
         "created_at": datetime.utcnow().isoformat() + "Z",
         "last_resumed_at": datetime.utcnow().isoformat() + "Z",
         "schema_version": "1.0"
       }
    2. Write to {sessions_dir}/{session_name}.meta.json
    3. Use json.dump() with indent=2 for readability
    4. Ensure directory exists: sessions_dir.mkdir(parents=True, exist_ok=True)
    """


def load_session_metadata(session_name: str, sessions_dir: Path) -> SessionMetadata:
    """
    Load metadata from .meta.json file.

    Implementation:
    1. Build path: sessions_dir / f"{session_name}.meta.json"
    2. Check exists: if not: raise FileNotFoundError
    3. Read JSON: with open() as f: data = json.load(f)
    4. Parse datetimes:
       - created_at = datetime.fromisoformat(data['created_at'].rstrip('Z'))
       - last_resumed_at = datetime.fromisoformat(data['last_resumed_at'].rstrip('Z'))
    5. Return SessionMetadata(
         session_name=data['session_name'],
         agent=data.get('agent'),  # Can be null
         project_dir=Path(data['project_dir']),
         agents_dir=Path(data['agents_dir']),
         created_at=created_at,
         last_resumed_at=last_resumed_at,
         schema_version=data.get('schema_version', 'legacy')
       )

    Raises:
        FileNotFoundError: If meta.json doesn't exist
        json.JSONDecodeError: If invalid JSON
        KeyError: If required fields missing
    """


def update_session_metadata(session_name: str, sessions_dir: Path) -> None:
    """
    Update last_resumed_at timestamp.

    Implementation:
    1. Load existing metadata JSON
    2. Update: data['last_resumed_at'] = datetime.utcnow().isoformat() + "Z"
    3. Write back to file atomically:
       - Write to temp file: .meta.json.tmp
       - Use json.dump(data, f, indent=2)
       - Rename temp to original: os.replace(tmp, meta_file)
    """


def extract_session_id(session_file: Path) -> str:
    """
    Extract Claude session_id from first line of .jsonl file.

    Implementation (from bash extract_session_id):
    1. Open session_file
    2. Read first line
    3. Parse JSON: first_line = json.loads(line)
    4. Extract: session_id = first_line.get('session_id')
    5. If missing or empty: raise ValueError("No session_id in first line")
    6. Return session_id

    Raises:
        FileNotFoundError: If session file doesn't exist
        json.JSONDecodeError: If first line isn't valid JSON
        ValueError: If session_id field missing
    """


def extract_result(session_file: Path) -> str:
    """
    Extract result from last line of .jsonl file.

    Implementation (from bash extract_result):
    1. Read last line (same efficient method as get_session_status)
    2. Parse JSON: last_msg = json.loads(last_line)
    3. Extract: result = last_msg.get('result')
    4. If missing or empty: raise ValueError("No result in last line")
    5. Return result string

    Raises:
        FileNotFoundError: If session file doesn't exist
        json.JSONDecodeError: If last line isn't valid JSON
        ValueError: If result field missing or session not finished
    """


def list_all_sessions(sessions_dir: Path) -> list[tuple[str, str, str]]:
    """
    List all sessions with basic info.

    Implementation (from bash cmd_list):
    1. Ensure sessions_dir exists: if not, return []
    2. Find all .jsonl files: sessions_dir.glob("*.jsonl")
    3. For each session_file:
       a. Extract session_name: session_file.stem
       b. Try to get session_id:
          - If file has content: read first line, parse session_id
          - If empty or error: session_id = "initializing"
       c. Try to get project_dir:
          - Load meta.json, get project_dir field
          - If error: project_dir = "unknown"
       d. Append tuple: (session_name, session_id, project_dir)
    4. Return list of tuples

    Returns:
        List of (session_name, session_id, project_dir) tuples
    """
```

**SDK Integration**: None (file operations only)

**Dependencies**: `pathlib`, `json`, `datetime`, `os`, `typing`, `dataclasses`, `re`

---

### 4.3 lib/agent.py

**Purpose**: Load and parse agent definitions (agent.json, system prompts, MCP configs)

**Key Functions**:

```python
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import json


@dataclass
class AgentConfig:
    """Agent configuration loaded from agent.json"""
    name: str
    description: str
    system_prompt: Optional[str]  # Content of agent.system-prompt.md
    mcp_config: Optional[dict]    # Parsed agent.mcp.json


def load_agent_config(agent_name: str, agents_dir: Path) -> AgentConfig:
    """
    Load agent configuration from directory.

    Implementation (from bash load_agent_config):
    1. Build paths:
       agent_dir = agents_dir / agent_name
       agent_file = agent_dir / "agent.json"
       prompt_file = agent_dir / "agent.system-prompt.md"
       mcp_file = agent_dir / "agent.mcp.json"

    2. Validate agent_dir exists:
       if not agent_dir.is_dir():
           raise FileNotFoundError(f"Agent not found: {agent_name} (expected: {agent_dir})")

    3. Validate agent.json exists:
       if not agent_file.exists():
           raise FileNotFoundError(f"Agent config not found: {agent_file}")

    4. Parse agent.json:
       with open(agent_file) as f:
           data = json.load(f)
       name = data['name']
       description = data['description']

    5. Validate name matches directory:
       if name != agent_name:
           raise ValueError(f"Name mismatch: folder={agent_name}, config={name}")

    6. Load system prompt (optional):
       system_prompt = None
       if prompt_file.exists():
           system_prompt = prompt_file.read_text()

    7. Load MCP config (optional):
       mcp_config = None
       if mcp_file.exists():
           with open(mcp_file) as f:
               mcp_config = json.load(f)

    8. Return AgentConfig(
           name=name,
           description=description,
           system_prompt=system_prompt,
           mcp_config=mcp_config
       )

    Raises:
        FileNotFoundError: If agent directory or agent.json missing
        json.JSONDecodeError: If JSON files malformed
        KeyError: If required fields missing from agent.json
        ValueError: If name doesn't match directory
    """


def list_all_agents(agents_dir: Path) -> list[tuple[str, str]]:
    """
    List all available agent definitions.

    Implementation (from bash cmd_list_agents):
    1. Ensure agents_dir exists: if not, return []
    2. Find all subdirectories: agents_dir.iterdir()
    3. For each subdir:
       a. Check if agent.json exists: subdir / "agent.json"
       b. If exists:
          - Parse JSON: load name and description
          - Append tuple: (name, description)
       c. If error: skip this directory
    4. Sort by name: sorted(agents, key=lambda x: x[0])
    5. Return list of (name, description) tuples

    Returns:
        List of (agent_name, description) tuples, sorted by name
    """


def build_mcp_servers_dict(mcp_config: Optional[dict]) -> dict:
    """
    Convert agent MCP config to Claude SDK format.

    Implementation:
    1. If mcp_config is None: return {}
    2. Extract mcpServers dict: mcp_config.get('mcpServers', {})
    3. Return dict as-is (SDK expects same format as .mcp.json)

    Note: The SDK's mcp_servers parameter expects dict with structure:
    {
      "server-name": {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-filesystem"],
        "env": {"VAR": "value"}
      }
    }

    This matches the mcpServers field in agent.mcp.json, so direct passthrough.
    """
```

**SDK Integration**: MCP config dict passed to `ClaudeAgentOptions.mcp_servers`

**Dependencies**: `pathlib`, `json`, `typing`, `dataclasses`

---

### 4.4 lib/claude_client.py

**Purpose**: Wrapper around Claude Agent SDK for session execution

**Key Functions**:

```python
from pathlib import Path
from typing import Optional
import json
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions


async def run_claude_session(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
) -> tuple[str, str]:
    """
    Run Claude session and stream output to .jsonl file.

    Args:
        prompt: User prompt (may include prepended system prompt from agent)
        session_file: Path to .jsonl file to append messages
        project_dir: Working directory for Claude (sets cwd)
        mcp_servers: MCP server configuration dict (from agent.mcp.json)
        resume_session_id: If provided, resume existing session

    Returns:
        Tuple of (session_id, result)

    Implementation:
    1. Build ClaudeAgentOptions:
       options = ClaudeAgentOptions(
           cwd=str(project_dir.resolve()),
           permission_mode="bypassPermissions",
       )

       if resume_session_id:
           options.resume = resume_session_id

       if mcp_servers:
           options.mcp_servers = mcp_servers

    2. Initialize tracking:
       session_id = None
       result = None

    3. Stream session to file:
       async for message in query(prompt=prompt, options=options):
           # Write each message to JSONL file (append mode)
           with open(session_file, 'a') as f:
               json.dump(message.model_dump(), f)
               f.write('\n')

           # Capture session_id from first message that has it
           if session_id is None and hasattr(message, 'session_id'):
               session_id = message.session_id

           # Capture result from last message (overwrite each time)
           if hasattr(message, 'result'):
               result = message.result

    4. Validate required data:
       if not session_id:
           raise ValueError("No session_id received from Claude")
       if not result:
           raise ValueError("No result received from Claude")

    5. Return tuple:
       return (session_id, result)

    Raises:
        ValueError: If session_id or result not found in messages
        SDKError: If Claude SDK raises errors
    """


def run_session_sync(
    prompt: str,
    session_file: Path,
    project_dir: Path,
    mcp_servers: Optional[dict] = None,
    resume_session_id: Optional[str] = None,
) -> tuple[str, str]:
    """
    Synchronous wrapper for run_claude_session.

    Implementation:
    Use asyncio.run() to execute async function from sync context:

    return asyncio.run(
        run_claude_session(
            prompt=prompt,
            session_file=session_file,
            project_dir=project_dir,
            mcp_servers=mcp_servers,
            resume_session_id=resume_session_id,
        )
    )

    This allows command scripts to remain synchronous while using SDK's async API.
    """
```

**SDK Integration**: Direct usage of `query()` and `ClaudeAgentOptions`

**Critical SDK Parameters**:
- `cwd`: Set to project_dir for consistent working directory
- `permission_mode`: Always "bypassPermissions" (matches bash `--permission-mode`)
- `resume`: Session ID for resuming
- `mcp_servers`: MCP configuration dict

**Dependencies**: `claude_agent_sdk`, `pathlib`, `json`, `typing`, `asyncio`

---

### 4.5 lib/utils.py

**Purpose**: Common utility functions

**Key Functions**:

```python
from pathlib import Path
from typing import Optional
import sys


def get_prompt_from_args_and_stdin(prompt_arg: Optional[str]) -> str:
    """
    Get prompt from -p flag and/or stdin.

    Implementation (from bash get_prompt):
    1. Initialize: final_prompt = ""
    2. If prompt_arg provided: final_prompt = prompt_arg
    3. Check if stdin has data:
       - Use sys.stdin.isatty() - False means stdin is piped
       - If not isatty():
           stdin_content = sys.stdin.read()
           if stdin_content:
               if final_prompt:
                   final_prompt = final_prompt + "\n" + stdin_content
               else:
                   final_prompt = stdin_content
    4. If final_prompt is empty: raise ValueError("No prompt provided")
    5. Return final_prompt

    Raises:
        ValueError: If no prompt from -p or stdin
    """


def error_exit(message: str, exit_code: int = 1) -> None:
    """
    Print error message to stderr and exit.

    Implementation:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(exit_code)
    """


def ensure_directory_exists(path: Path) -> None:
    """
    Create directory if it doesn't exist.

    Implementation:
    path.mkdir(parents=True, exist_ok=True)
    """


def log_command(
    session_name: str,
    command_type: str,
    agent_name: Optional[str],
    mcp_config_path: Optional[str],
    full_command: str,
    prompt: str,
    sessions_dir: Path,
    project_dir: Path,
    agents_dir: Path,
    enable_logging: bool,
) -> None:
    """
    Log command execution to .log file (if logging enabled).

    Implementation (from bash log_command):
    1. Check if logging enabled: if not enable_logging: return
    2. Build log entry:
       timestamp = datetime.utcnow().isoformat() + "Z"
       log_file = sessions_dir / f"{session_name}.log"

       entry = f'''
       ================================================================================
       Timestamp: {timestamp}
       Command Type: {command_type}
       Working Directory: {project_dir}
       Agents Directory: {agents_dir}
       Agent Name: {agent_name or "none"}
       MCP Config: {mcp_config_path or "none"}

       Full Command:
       {full_command}

       Environment:
       AGENT_ORCHESTRATOR_PROJECT_DIR={os.environ.get('AGENT_ORCHESTRATOR_PROJECT_DIR', 'not set')}
       AGENT_ORCHESTRATOR_AGENTS_DIR={os.environ.get('AGENT_ORCHESTRATOR_AGENTS_DIR', 'not set')}
       AGENT_ORCHESTRATOR_SESSIONS_DIR={os.environ.get('AGENT_ORCHESTRATOR_SESSIONS_DIR', 'not set')}
       AGENT_ORCHESTRATOR_ENABLE_LOGGING={os.environ.get('AGENT_ORCHESTRATOR_ENABLE_LOGGING', 'not set')}

       Prompt:
       {prompt}
       ================================================================================

       '''
    3. Append to log file:
       with open(log_file, 'a') as f:
           f.write(entry)
    """


def log_result(
    session_name: str,
    result: str,
    sessions_dir: Path,
    enable_logging: bool,
) -> None:
    """
    Log result to .log file (if logging enabled).

    Implementation:
    Similar to log_command, append result section to .log file
    """
```

**SDK Integration**: None (utilities)

**Dependencies**: `pathlib`, `sys`, `typing`, `os`, `datetime`

---

## 5. Command Scripts (commands/)

### Command Script Pattern

All command scripts follow this structure:

1. **Parse arguments** - Use argparse with consistent CLI interface
2. **Validate inputs** - Session name validation, path validation
3. **Load configuration** - CLI > ENV > DEFAULT precedence
4. **Execute command** - Call lib functions to perform operation
5. **Handle errors** - Graceful error messages, proper exit codes
6. **Output results** - Print to stdout (errors to stderr)

### 5.1 commands/ao-new

See ARCHITECTURE_PLAN.md section 5.1 for complete implementation guidance.

### 5.2 commands/ao-resume

See ARCHITECTURE_PLAN.md section 5.2 for complete implementation guidance.

### 5.3 commands/ao-status

See ARCHITECTURE_PLAN.md section 5.3 for complete implementation guidance.

### 5.4 commands/ao-get-result

See ARCHITECTURE_PLAN.md section 5.4 for complete implementation guidance.

### 5.5 commands/ao-list-sessions

See ARCHITECTURE_PLAN.md section 5.5 for complete implementation guidance.

### 5.6 commands/ao-list-agents

See ARCHITECTURE_PLAN.md section 5.6 for complete implementation guidance.

### 5.7 commands/ao-show-config

See ARCHITECTURE_PLAN.md section 5.7 for complete implementation guidance.

### 5.8 commands/ao-clean

See ARCHITECTURE_PLAN.md section 5.8 for complete implementation guidance.

---

## 6. Environment Variable Management

### 6.1 Centralized Strategy

All environment variable access happens in `lib/config.py`:

```python
# lib/config.py

import os

# Environment variable names (MUST NOT CHANGE - compatibility with bash)
ENV_PROJECT_DIR = "AGENT_ORCHESTRATOR_PROJECT_DIR"
ENV_SESSIONS_DIR = "AGENT_ORCHESTRATOR_SESSIONS_DIR"
ENV_AGENTS_DIR = "AGENT_ORCHESTRATOR_AGENTS_DIR"
ENV_ENABLE_LOGGING = "AGENT_ORCHESTRATOR_ENABLE_LOGGING"


def get_env_project_dir() -> Optional[str]:
    """Get project_dir from environment."""
    return os.environ.get(ENV_PROJECT_DIR)


def get_env_sessions_dir() -> Optional[str]:
    """Get sessions_dir from environment."""
    return os.environ.get(ENV_SESSIONS_DIR)


def get_env_agents_dir() -> Optional[str]:
    """Get agents_dir from environment."""
    return os.environ.get(ENV_AGENTS_DIR)


def get_env_logging_enabled() -> bool:
    """Check if logging is enabled via environment."""
    value = os.environ.get(ENV_ENABLE_LOGGING, "").lower()
    return value in ("1", "true", "yes")
```

### 6.2 Complete Environment Variable List

| Variable | Purpose | Values | Used In |
|----------|---------|--------|---------|
| `AGENT_ORCHESTRATOR_PROJECT_DIR` | Default project directory | Path string | `config.py` |
| `AGENT_ORCHESTRATOR_SESSIONS_DIR` | Override sessions directory | Path string | `config.py` |
| `AGENT_ORCHESTRATOR_AGENTS_DIR` | Override agents directory | Path string | `config.py` |
| `AGENT_ORCHESTRATOR_ENABLE_LOGGING` | Enable command logging | `1`, `true`, `yes` | `config.py` |

### 6.3 Precedence Rules

```
For each configuration value:
1. CLI flag value (if provided)
2. Environment variable value (if set)
3. Default value (PWD-based)
```

---

## 7. File Format Compatibility

### 7.1 Session File Format (`.jsonl`)

- **Format**: JSON Lines (stream-json from Claude CLI/SDK)
- **First line**: Contains `session_id` field
- **Last line**: Contains `type: "result"` and `result` field

### 7.2 Metadata File Format (`.meta.json`)

```json
{
  "session_name": "architect",
  "agent": "system-architect",
  "project_dir": "/absolute/path/to/project",
  "agents_dir": "/absolute/path/to/agents",
  "created_at": "2025-01-15T10:30:00Z",
  "last_resumed_at": "2025-01-15T11:45:00Z",
  "schema_version": "1.0"
}
```

### 7.3 Agent Structure

```
agents/
└── system-architect/
    ├── agent.json              # Required
    ├── agent.system-prompt.md  # Optional
    └── agent.mcp.json          # Optional
```

---

## 8. Implementation Roadmap

### Phase 1: Core Infrastructure (Read-Only)
1. Implement `lib/config.py`
2. Implement `lib/utils.py`
3. Implement `lib/session.py`
4. Implement `commands/ao-status`
5. Implement `commands/ao-list-sessions`
6. Implement `commands/ao-show-config`

### Phase 2: Agent Loading
1. Implement `lib/agent.py`
2. Implement `commands/ao-list-agents`

### Phase 3: Claude SDK Integration
1. Implement `lib/claude_client.py`
2. Test basic session creation

### Phase 4: Write Operations
1. Implement `commands/ao-new`
2. Implement `commands/ao-resume`
3. Implement `commands/ao-get-result`
4. Implement `commands/ao-clean`

### Phase 5: Testing & Documentation
1. Create comprehensive test suite
2. Test bash/Python interoperability
3. Update documentation

---

## Summary

This architectural plan provides complete guidance for implementing a Python-based agent orchestrator that:

- ✅ Uses Claude Agent Python SDK directly
- ✅ Maintains 100% compatibility with bash script
- ✅ Implements progressive disclosure architecture
- ✅ Provides centralized configuration management
- ✅ Includes sophisticated implementation hints
- ✅ Supports all existing features and file formats
