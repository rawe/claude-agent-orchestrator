#!/bin/bash

set -euo pipefail

# Constants
MAX_NAME_LENGTH=60

# Directory configuration (set by init_directories)
PROJECT_DIR=""
AGENT_SESSIONS_DIR=""
AGENTS_DIR=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Show help message
show_help() {
  cat << EOF
Usage:
  agent-orchestrator.sh [global-options] new <session-name> [--agent <agent-name>] [-p <prompt>]
  agent-orchestrator.sh [global-options] resume <session-name> [-p <prompt>]
  agent-orchestrator.sh [global-options] status <session-name>
  agent-orchestrator.sh [global-options] list
  agent-orchestrator.sh [global-options] list-agents
  agent-orchestrator.sh [global-options] clean

Commands:
  new          Create a new session (optionally with an agent)
  resume       Resume an existing session
  status       Check the status of a session (returns: running, finished, or not_existent)
  list         List all sessions with metadata
  list-agents  List all available agent definitions
  clean        Remove all sessions

Arguments:
  <session-name>  Name of the session (alphanumeric, dash, underscore only; max 60 chars)
  <agent-name>    Name of the agent definition to use (optional for new command)

Global Options (before command):
  --project-dir <path>   Set project directory (default: current directory)
  --sessions-dir <path>  Override sessions directory location
  --agents-dir <path>    Override agents directory location

Command Options:
  -p <prompt>     Session prompt (can be combined with stdin; -p content comes first)
  --agent <name>  Use a specific agent definition (only for new command)

Environment Variables:
  AGENT_ORCHESTRATOR_PROJECT_DIR   Set default project directory
  AGENT_ORCHESTRATOR_SESSIONS_DIR  Set default sessions directory
  AGENT_ORCHESTRATOR_AGENTS_DIR    Set default agents directory

  Precedence order (highest to lowest):
    1. CLI flags (--project-dir, --sessions-dir, --agents-dir)
    2. Environment variables
    3. Current directory (PWD)

Examples:
  # Create new session (generic, no agent)
  ./agent-orchestrator.sh new architect -p "Design user auth system"

  # Create new session with agent
  ./agent-orchestrator.sh new architect --agent system-architect -p "Design user auth system"

  # Create new session from file
  cat prompt.md | ./agent-orchestrator.sh new architect --agent system-architect

  # Resume session (agent association remembered)
  ./agent-orchestrator.sh resume architect -p "Continue with API design"

  # Resume from file
  cat continue.md | ./agent-orchestrator.sh resume architect

  # Combine -p and stdin (concatenated)
  cat requirements.md | ./agent-orchestrator.sh new architect -p "Create architecture based on:"

  # Check session status
  ./agent-orchestrator.sh status architect

  # List all sessions
  ./agent-orchestrator.sh list

  # List all agent definitions
  ./agent-orchestrator.sh list-agents

  # Remove all sessions
  ./agent-orchestrator.sh clean

  # Use custom project directory
  ./agent-orchestrator.sh --project-dir /path/to/project new session -p "prompt"

  # Share agents across projects, keep sessions local
  ./agent-orchestrator.sh --agents-dir ~/shared/agents new session --agent my-agent -p "prompt"

  # Use environment variables
  export AGENT_ORCHESTRATOR_PROJECT_DIR=/path/to/project
  ./agent-orchestrator.sh new session -p "prompt"

  # CLI flags override environment variables
  export AGENT_ORCHESTRATOR_PROJECT_DIR=/tmp/env-project
  ./agent-orchestrator.sh --project-dir /tmp/cli-project new session -p "prompt"  # Uses /tmp/cli-project
EOF
}

# Error message helper
error() {
  echo -e "${RED}Error: $1${NC}" >&2
  exit 1
}

# Resolve path to absolute path
resolve_absolute_path() {
  local path="$1"

  # If path is empty, return empty
  if [ -z "$path" ]; then
    echo ""
    return
  fi

  # Try to resolve the path
  if [ -d "$path" ]; then
    # Directory exists, get absolute path
    (cd "$path" 2>/dev/null && pwd) || echo "$path"
  else
    # Directory doesn't exist, try to resolve relative to PWD
    if [[ "$path" = /* ]]; then
      # Already absolute
      echo "$path"
    else
      # Make it absolute relative to PWD
      echo "$(pwd)/$path"
    fi
  fi
}

# Find the first existing parent directory
find_existing_parent() {
  local dir="$1"
  local current="$dir"

  while [ "$current" != "/" ] && [ "$current" != "." ]; do
    if [ -d "$current" ]; then
      echo "$current"
      return
    fi
    current=$(dirname "$current")
  done

  echo "/"
}

# Validate directory configuration
validate_directories() {
  # Validate PROJECT_DIR exists and is readable
  if [ ! -d "$PROJECT_DIR" ]; then
    error "Project directory does not exist: $PROJECT_DIR"
  fi

  if [ ! -r "$PROJECT_DIR" ]; then
    error "Project directory is not readable: $PROJECT_DIR"
  fi

  # For AGENT_SESSIONS_DIR and AGENTS_DIR, validate that we can create them
  # Find the first existing parent and check if it's writable
  if [ ! -d "$AGENT_SESSIONS_DIR" ]; then
    local sessions_existing_parent
    sessions_existing_parent=$(find_existing_parent "$AGENT_SESSIONS_DIR")
    if [ ! -w "$sessions_existing_parent" ]; then
      error "Cannot create sessions directory (parent not writable): $AGENT_SESSIONS_DIR\nExisting parent: $sessions_existing_parent"
    fi
  fi

  if [ ! -d "$AGENTS_DIR" ]; then
    local agents_existing_parent
    agents_existing_parent=$(find_existing_parent "$AGENTS_DIR")
    if [ ! -w "$agents_existing_parent" ]; then
      error "Cannot create agents directory (parent not writable): $AGENTS_DIR\nExisting parent: $agents_existing_parent"
    fi
  fi
}

# Initialize directory configuration
# Precedence: 1. CLI flags, 2. Environment variables, 3. PWD default
# Sets global variables: PROJECT_DIR, AGENT_SESSIONS_DIR, AGENTS_DIR, REMAINING_ARGS
init_directories() {
  # Defaults
  local default_project_dir="$PWD"

  # Environment variables (second priority)
  local env_project_dir="${AGENT_ORCHESTRATOR_PROJECT_DIR:-}"
  local env_sessions_dir="${AGENT_ORCHESTRATOR_SESSIONS_DIR:-}"
  local env_agents_dir="${AGENT_ORCHESTRATOR_AGENTS_DIR:-}"

  # CLI flags (first priority)
  local cli_project_dir=""
  local cli_sessions_dir=""
  local cli_agents_dir=""

  # Parse global flags
  REMAINING_ARGS=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project-dir)
        if [ $# -lt 2 ]; then
          error "--project-dir flag requires a directory path"
        fi
        cli_project_dir="$2"
        shift 2
        ;;
      --sessions-dir)
        if [ $# -lt 2 ]; then
          error "--sessions-dir flag requires a directory path"
        fi
        cli_sessions_dir="$2"
        shift 2
        ;;
      --agents-dir)
        if [ $# -lt 2 ]; then
          error "--agents-dir flag requires a directory path"
        fi
        cli_agents_dir="$2"
        shift 2
        ;;
      *)
        # Not a global flag, save for command processing
        REMAINING_ARGS+=("$1")
        shift
        ;;
    esac
  done

  # Apply precedence: CLI > ENV > DEFAULT
  if [ -n "$cli_project_dir" ]; then
    PROJECT_DIR="$cli_project_dir"
  elif [ -n "$env_project_dir" ]; then
    PROJECT_DIR="$env_project_dir"
  else
    PROJECT_DIR="$default_project_dir"
  fi

  # Resolve to absolute path
  PROJECT_DIR=$(resolve_absolute_path "$PROJECT_DIR")

  # Set derived directories with override support
  if [ -n "$cli_sessions_dir" ]; then
    AGENT_SESSIONS_DIR=$(resolve_absolute_path "$cli_sessions_dir")
  elif [ -n "$env_sessions_dir" ]; then
    AGENT_SESSIONS_DIR=$(resolve_absolute_path "$env_sessions_dir")
  else
    AGENT_SESSIONS_DIR="$PROJECT_DIR/.agent-orchestrator/agent-sessions"
  fi

  if [ -n "$cli_agents_dir" ]; then
    AGENTS_DIR=$(resolve_absolute_path "$cli_agents_dir")
  elif [ -n "$env_agents_dir" ]; then
    AGENTS_DIR=$(resolve_absolute_path "$env_agents_dir")
  else
    AGENTS_DIR="$PROJECT_DIR/.agent-orchestrator/agents"
  fi

  # Validate directory configuration
  validate_directories
}

# Ensure required directories exist
ensure_directories() {
  mkdir -p "$AGENT_SESSIONS_DIR"
  mkdir -p "$AGENTS_DIR"
}

# Validate session name
validate_session_name() {
  local name="$1"

  # Check if empty
  if [ -z "$name" ]; then
    error "Session name cannot be empty"
  fi

  # Check length
  if [ ${#name} -gt $MAX_NAME_LENGTH ]; then
    error "Session name too long (max $MAX_NAME_LENGTH characters): $name"
  fi

  # Check for valid characters (alphanumeric, dash, underscore only)
  if [[ ! "$name" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    error "Session name contains invalid characters. Only alphanumeric, dash (-), and underscore (_) are allowed: $name"
  fi
}

# Get prompt from -p flag and/or stdin
get_prompt() {
  local prompt_arg="$1"
  local final_prompt=""

  # Add -p content first if provided
  if [ -n "$prompt_arg" ]; then
    final_prompt="$prompt_arg"
  fi

  # Check if stdin has data
  if [ ! -t 0 ]; then
    # Read from stdin
    local stdin_content
    stdin_content=$(cat)
    if [ -n "$stdin_content" ]; then
      # If we already have prompt from -p, add newline separator
      if [ -n "$final_prompt" ]; then
        final_prompt="${final_prompt}"$'\n'"${stdin_content}"
      else
        final_prompt="$stdin_content"
      fi
    fi
  fi

  # Check if we got any prompt at all
  if [ -z "$final_prompt" ]; then
    error "No prompt provided. Use -p flag or pipe prompt via stdin"
  fi

  echo "$final_prompt"
}

# Extract result from last line of agent session file
extract_result() {
  local session_file="$1"

  if [ ! -f "$session_file" ]; then
    error "Session file not found: $session_file"
  fi

  local result
  result=$(tail -n 1 "$session_file" | jq -r '.result // empty' 2>/dev/null)

  if [ -z "$result" ]; then
    error "Could not extract result from session file"
  fi

  echo "$result"
}

# Extract session_id from first line of agent session file
extract_session_id() {
  local session_file="$1"

  if [ ! -f "$session_file" ]; then
    error "Session file not found: $session_file"
  fi

  local session_id
  session_id=$(head -n 1 "$session_file" | jq -r '.session_id // empty' 2>/dev/null)

  if [ -z "$session_id" ]; then
    error "Could not extract session_id from session file"
  fi

  echo "$session_id"
}

# Load agent configuration from agent directory
# Args: $1 - Agent name (must match folder name)
# Sets global vars: AGENT_NAME, AGENT_DESCRIPTION, SYSTEM_PROMPT_FILE (full path), MCP_CONFIG (full path)
load_agent_config() {
  local agent_name="$1"
  local agent_dir="$AGENTS_DIR/${agent_name}"
  local agent_file="$agent_dir/agent.json"

  if [ ! -d "$agent_dir" ]; then
    error "Agent not found: $agent_name (expected directory: $agent_dir)"
  fi

  if [ ! -f "$agent_file" ]; then
    error "Agent configuration not found: $agent_file"
  fi

  # Validate JSON
  if ! jq empty "$agent_file" 2>/dev/null; then
    error "Invalid JSON in agent configuration: $agent_file"
  fi

  # Extract fields
  AGENT_NAME=$(jq -r '.name' "$agent_file")
  AGENT_DESCRIPTION=$(jq -r '.description' "$agent_file")

  # Validate name matches folder name
  if [ "$AGENT_NAME" != "$agent_name" ]; then
    error "Agent name mismatch: folder=$agent_name, config name=$AGENT_NAME"
  fi

  # Check for optional files by convention
  SYSTEM_PROMPT_FILE=""
  if [ -f "$agent_dir/agent.system-prompt.md" ]; then
    SYSTEM_PROMPT_FILE="$agent_dir/agent.system-prompt.md"
  fi

  MCP_CONFIG=""
  if [ -f "$agent_dir/agent.mcp.json" ]; then
    MCP_CONFIG="$agent_dir/agent.mcp.json"
  fi
}

# Load system prompt from file and return its content
# Args: $1 - Full path to prompt file (already resolved by load_agent_config)
# Returns: File content via stdout, or empty string if path is empty
load_system_prompt() {
  local prompt_file="$1"

  if [ -z "$prompt_file" ]; then
    echo ""
    return
  fi

  if [ ! -f "$prompt_file" ]; then
    error "System prompt file not found: $prompt_file"
  fi

  cat "$prompt_file"
}

# Save session metadata
save_session_metadata() {
  local session_name="$1"
  local agent_name="$2"  # Can be empty for generic sessions
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  local meta_file="$AGENT_SESSIONS_DIR/${session_name}.meta.json"

  cat > "$meta_file" <<EOF
{
  "session_name": "$session_name",
  "agent": $([ -n "$agent_name" ] && echo "\"$agent_name\"" || echo "null"),
  "created_at": "$timestamp",
  "last_resumed_at": "$timestamp"
}
EOF
}

# Load session metadata
load_session_metadata() {
  local session_name="$1"
  local meta_file="$AGENT_SESSIONS_DIR/${session_name}.meta.json"

  if [ ! -f "$meta_file" ]; then
    # No metadata - treat as generic session (backward compatibility)
    SESSION_AGENT=""
    return
  fi

  SESSION_AGENT=$(jq -r '.agent // empty' "$meta_file")
}

# Update session metadata timestamp
update_session_metadata() {
  local session_name="$1"
  local agent_name="$2"  # Optional: agent name if known
  local meta_file="$AGENT_SESSIONS_DIR/${session_name}.meta.json"
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  if [ -f "$meta_file" ]; then
    # Update last_resumed_at
    jq ".last_resumed_at = \"$timestamp\"" "$meta_file" > "${meta_file}.tmp"
    mv "${meta_file}.tmp" "$meta_file"
  else
    # Create meta.json if it doesn't exist (backward compatibility)
    save_session_metadata "$session_name" "$agent_name"
  fi
}

# Build MCP config argument for Claude CLI
# Args: $1 - Full path to MCP config file (already resolved by load_agent_config)
# Returns: Claude CLI argument string "--mcp-config <path>", or empty string if path is empty
build_mcp_arg() {
  local mcp_config="$1"

  if [ -z "$mcp_config" ]; then
    echo ""
    return
  fi

  if [ ! -f "$mcp_config" ]; then
    error "MCP config file not found: $mcp_config"
  fi

  echo "--mcp-config $mcp_config"
}

# Command: new
cmd_new() {
  local session_name="$1"
  local prompt_arg="$2"
  local agent_name="$3"  # Optional

  validate_session_name "$session_name"

  local session_file="$AGENT_SESSIONS_DIR/${session_name}.jsonl"

  # Check if session already exists
  if [ -f "$session_file" ]; then
    error "Session '$session_name' already exists. Use 'resume' command to continue or choose a different name"
  fi

  # Get user prompt
  local user_prompt
  user_prompt=$(get_prompt "$prompt_arg")

  # Load agent configuration if specified
  local final_prompt="$user_prompt"
  local mcp_arg=""

  if [ -n "$agent_name" ]; then
    load_agent_config "$agent_name"

    # Load and prepend system prompt
    if [ -n "$SYSTEM_PROMPT_FILE" ]; then
      local system_prompt
      system_prompt=$(load_system_prompt "$SYSTEM_PROMPT_FILE")
      final_prompt="${system_prompt}"$'\n\n---\n\n'"${user_prompt}"
    fi

    # Build MCP argument
    mcp_arg=$(build_mcp_arg "$MCP_CONFIG")
  fi

  # Ensure required directories exist
  ensure_directories

  # Save session metadata immediately
  save_session_metadata "$session_name" "$agent_name"

  # Run claude command
  if ! claude -p "$final_prompt" $mcp_arg --output-format stream-json --permission-mode bypassPermissions >> "$session_file" 2>&1; then
    error "Claude command failed"
  fi

  # Extract and output result
  extract_result "$session_file"
}

# Command: resume
cmd_resume() {
  local session_name="$1"
  local prompt_arg="$2"

  validate_session_name "$session_name"

  local session_file="$AGENT_SESSIONS_DIR/${session_name}.jsonl"

  # Check if session exists
  if [ ! -f "$session_file" ]; then
    error "Session '$session_name' does not exist. Use 'new' command to create it"
  fi

  # Load session metadata to get agent
  load_session_metadata "$session_name"

  # Extract session_id
  local session_id
  session_id=$(extract_session_id "$session_file")

  # Get prompt
  local prompt
  prompt=$(get_prompt "$prompt_arg")

  # Load agent configuration if session has an agent
  local mcp_arg=""
  if [ -n "$SESSION_AGENT" ]; then
    load_agent_config "$SESSION_AGENT"
    mcp_arg=$(build_mcp_arg "$MCP_CONFIG")
  fi

  # Run claude command with resume
  if ! claude -r "$session_id" -p "$prompt" $mcp_arg --output-format stream-json --permission-mode bypassPermissions >> "$session_file" 2>&1; then
    error "Claude resume command failed"
  fi

  # Update session metadata timestamp (or create if missing)
  update_session_metadata "$session_name" "$SESSION_AGENT"

  # Extract and output result
  extract_result "$session_file"
}

# Command: status
cmd_status() {
  local session_name="$1"

  validate_session_name "$session_name"

  local meta_file="$AGENT_SESSIONS_DIR/${session_name}.meta.json"
  local session_file="$AGENT_SESSIONS_DIR/${session_name}.jsonl"

  # Check if meta.json exists (primary indicator of session existence)
  if [ ! -f "$meta_file" ]; then
    echo "not_existent"
    return
  fi

  # Check if session file exists
  if [ ! -f "$session_file" ]; then
    # Meta exists but no session file - initializing state
    echo "running"
    return
  fi

  # Check if file is empty (initializing state)
  if [ ! -s "$session_file" ]; then
    echo "running"
    return
  fi

  # Check last line for type=result
  local last_line
  last_line=$(tail -n 1 "$session_file" 2>/dev/null)

  # If we can't read the last line, assume running
  if [ -z "$last_line" ]; then
    echo "running"
    return
  fi

  # Check if last line has type=result (indicates completion)
  if echo "$last_line" | jq -e '.type == "result"' > /dev/null 2>&1; then
    echo "finished"
  else
    echo "running"
  fi
}

# Command: list
cmd_list() {
  # Ensure required directories exist
  ensure_directories

  # Check if there are any sessions
  local session_files=("$AGENT_SESSIONS_DIR"/*.jsonl)

  if [ ! -f "${session_files[0]}" ]; then
    echo "No sessions found"
    return
  fi

  # List all sessions with metadata
  for session_file in "$AGENT_SESSIONS_DIR"/*.jsonl; do
    local session_name
    session_name=$(basename "$session_file" .jsonl)

    local session_id
    # Extract session_id without calling error function (for empty/initializing sessions)
    if [ -s "$session_file" ]; then
      session_id=$(head -n 1 "$session_file" 2>/dev/null | jq -r '.session_id // "unknown"' 2>/dev/null || echo "unknown")
    else
      session_id="initializing"
    fi

    echo "$session_name (session: $session_id)"
  done
}

# Command: list-agents - List all available agent definitions from agent directories
# Scans AGENTS_DIR for subdirectories containing agent.json files
# Outputs: Agent name and description in formatted list
cmd_list_agents() {
  # Ensure required directories exist
  ensure_directories

  # Check if there are any agent directories
  local found_agents=false
  for agent_dir in "$AGENTS_DIR"/*; do
    if [ -d "$agent_dir" ] && [ -f "$agent_dir/agent.json" ]; then
      found_agents=true
      break
    fi
  done

  if [ "$found_agents" = false ]; then
    echo "No agent definitions found"
    return
  fi

  # List all agent definitions
  local first=true
  for agent_dir in "$AGENTS_DIR"/*; do
    # Skip if not a directory or doesn't have agent.json
    if [ ! -d "$agent_dir" ] || [ ! -f "$agent_dir/agent.json" ]; then
      continue
    fi

    local agent_name
    local agent_description
    local agent_file="$agent_dir/agent.json"

    # Extract name and description from JSON
    agent_name=$(jq -r '.name // "unknown"' "$agent_file" 2>/dev/null)
    agent_description=$(jq -r '.description // "No description available"' "$agent_file" 2>/dev/null)

    # Add separator before each agent (except the first)
    if [ "$first" = true ]; then
      first=false
    else
      echo "---"
      echo ""
    fi

    # Display in requested format
    echo "${agent_name}:"
    echo "${agent_description}"
    echo ""
  done
}

# Command: clean
cmd_clean() {
  # Remove the entire agent-sessions directory
  if [ -d "$AGENT_SESSIONS_DIR" ]; then
    rm -rf "$AGENT_SESSIONS_DIR"
    echo "All sessions removed"
  else
    echo "No sessions to remove"
  fi
}

# Main script logic
main() {
  # Check if no arguments provided
  if [ $# -eq 0 ]; then
    show_help
    exit 1
  fi

  # Initialize directories from CLI flags, env vars, or defaults
  # This sets PROJECT_DIR, AGENT_SESSIONS_DIR, AGENTS_DIR, and REMAINING_ARGS
  init_directories "$@"

  # Check if we have any remaining arguments
  if [ ${#REMAINING_ARGS[@]} -eq 0 ]; then
    # No remaining args - show help
    show_help
    exit 1
  fi

  # Set positional parameters to remaining args
  set -- "${REMAINING_ARGS[@]}"

  local command="$1"
  shift

  case "$command" in
    new)
      # Parse arguments
      if [ $# -eq 0 ]; then
        error "Session name required for 'new' command"
      fi

      local session_name="$1"
      shift

      local prompt_arg=""
      local agent_name=""
      while [ $# -gt 0 ]; do
        case "$1" in
          -p)
            if [ $# -lt 2 ]; then
              error "-p flag requires a prompt argument"
            fi
            prompt_arg="$2"
            shift 2
            ;;
          --agent)
            if [ $# -lt 2 ]; then
              error "--agent flag requires an agent name"
            fi
            agent_name="$2"
            shift 2
            ;;
          *)
            error "Unknown option: $1"
            ;;
        esac
      done

      cmd_new "$session_name" "$prompt_arg" "$agent_name"
      ;;

    resume)
      # Parse arguments
      if [ $# -eq 0 ]; then
        error "Session name required for 'resume' command"
      fi

      local session_name="$1"
      shift

      local prompt_arg=""
      while [ $# -gt 0 ]; do
        case "$1" in
          -p)
            if [ $# -lt 2 ]; then
              error "-p flag requires a prompt argument"
            fi
            prompt_arg="$2"
            shift 2
            ;;
          *)
            error "Unknown option: $1"
            ;;
        esac
      done

      cmd_resume "$session_name" "$prompt_arg"
      ;;

    status)
      # Parse arguments
      if [ $# -eq 0 ]; then
        error "Session name required for 'status' command"
      fi

      local session_name="$1"
      shift

      # Check for unexpected arguments
      if [ $# -gt 0 ]; then
        error "Unknown option: $1"
      fi

      cmd_status "$session_name"
      ;;

    list)
      cmd_list
      ;;

    list-agents)
      cmd_list_agents
      ;;

    clean)
      cmd_clean
      ;;

    -h|--help)
      show_help
      exit 0
      ;;

    *)
      error "Unknown command: $command\n\nRun './agent-orchestrator.sh' for usage information"
      ;;
  esac
}

# Run main function
main "$@"
