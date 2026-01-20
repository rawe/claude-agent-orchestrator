#!/bin/bash
# =============================================================================
# Start Agent Runner for Claude Code - Development Mode
# =============================================================================
# - Executor: Claude Code (autonomous profile)
# - Connects to Agent Coordinator at http://localhost:8765
# - Project dir: .agent-orchestrator/runner-claude-code/
# - No auth required (coordinator must also run without auth)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RUNNER_PROJECT_DIR="$PROJECT_ROOT/.agent-orchestrator/runner-claude-code"

mkdir -p "$RUNNER_PROJECT_DIR"

PROJECT_DIR="$RUNNER_PROJECT_DIR" \
"$PROJECT_ROOT/servers/agent-runner/agent-runner"
