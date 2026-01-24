#!/bin/bash
# =============================================================================
# Start Agent Runner for Procedural Executor - Development Mode
# =============================================================================
# - Executor: Echo (procedural profile for testing)
# - Echoes commands instead of executing them via Claude Code
# - Useful for testing agent workflows without AI execution
# - Connects to Agent Coordinator at http://localhost:8765
# - Project dir: .agent-orchestrator/runner-workdir/ (shared with other runners)
# - No auth required (coordinator must also run without auth)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# TEMP: Shared workdir for all runners to test file access without complex sync mechanisms
RUNNER_PROJECT_DIR="$PROJECT_ROOT/.agent-orchestrator/runner-workdir"

mkdir -p "$RUNNER_PROJECT_DIR"

PROJECT_DIR="$RUNNER_PROJECT_DIR" \
"$PROJECT_ROOT/servers/agent-runner/agent-runner" -x echo -t uv
