#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///

import sys
import json
import httpx
from datetime import datetime, UTC

def main():
    """Stop hook - captures session completion"""
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract session completion data
        # Note: Claude Code provides transcript_path (JSONL file) but not exit_code or reason directly
        # Available fields: session_id, transcript_path, cwd, permission_mode, stop_hook_active
        #
        # TODO: To get exit_code and reason, we would need to:
        #   1. Read the transcript JSONL file from transcript_path
        #   2. Parse the last entries to determine completion status
        #   3. Extract error information or success status
        #   For now, we just capture that the session stopped.

        event = {
            "event_type": "session_stop",
            "session_id": hook_input.get("session_id", "unknown"),
            "session_name": hook_input.get("session_id", "unknown"),
            "timestamp": datetime.now(UTC).isoformat(),
            # transcript_path available at: hook_input.get("transcript_path")
            # This points to the session's JSONL file with full conversation history
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
