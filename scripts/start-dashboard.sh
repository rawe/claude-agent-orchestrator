#!/bin/bash
# =============================================================================
# Start Dashboard - Development Mode
# =============================================================================
# - Auth disabled (Auth0 env vars empty) - DO NOT USE IN PRODUCTION
# - Runs on http://localhost:3000
# - Connects to Agent Coordinator at http://localhost:8765
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/dashboard"

VITE_AUTH0_DOMAIN= \
VITE_AUTH0_CLIENT_ID= \
VITE_AUTH0_AUDIENCE= \
npm run dev
