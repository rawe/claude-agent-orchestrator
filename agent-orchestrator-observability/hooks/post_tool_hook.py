#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///

import sys
import json
import httpx
from datetime import datetime, UTC

def main():
    """PostToolUse hook - captures tool execution results"""
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract tool execution data
        event = {
            "event_type": "post_tool",
            "session_id": hook_input.get("session_id", "unknown"),
            "session_name": hook_input.get("session_id", "unknown"),
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_name": hook_input.get("tool_name", "unknown"),
            "tool_input": hook_input.get("tool_input", {}),
            "tool_output": hook_input.get("tool_response", ""),
            "error": hook_input.get("error"),
        }

        # Send to observability backend
        backend_url = "http://localhost:8765/events"

        try:
            httpx.post(backend_url, json=event, timeout=2.0)
        except Exception:
            # Fail silently - don't block agent execution if backend is down
            pass

    except Exception:
        # Fail silently - hooks should never crash the agent
        pass

    # Always exit successfully
    sys.exit(0)

if __name__ == "__main__":
    main()
