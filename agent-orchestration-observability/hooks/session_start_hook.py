#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///

import sys
import json
import httpx
from datetime import datetime, UTC

def main():
    """Hook to capture session start events"""
    try:
        hook_input = json.load(sys.stdin)
    except Exception as e:
        print(f"Error reading hook input: {e}", file=sys.stderr)
        sys.exit(0)

    event = {
        "event_type": "session_start",
        "session_id": hook_input.get("session_id", "unknown"),
        "session_name": hook_input.get("session_id", "unknown"),  # Use session_id as name for MVP
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        httpx.post(
            "http://127.0.0.1:8765/events",
            json=event,
            timeout=1.0
        )
    except Exception as e:
        # Don't fail the hook if backend is down
        print(f"Warning: Failed to send event to observability backend: {e}", file=sys.stderr)

    # Always succeed to not block agent execution
    sys.exit(0)

if __name__ == "__main__":
    main()
