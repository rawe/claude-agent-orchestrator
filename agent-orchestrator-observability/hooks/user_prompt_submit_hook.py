#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///

import sys
import json
import httpx
from datetime import datetime, UTC

def main():
    """UserPromptSubmit hook - captures user prompts as message events"""
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract user prompt
        prompt = hook_input.get("prompt", "")

        if not prompt:
            # No prompt to send
            return

        # Create message event with user role
        event = {
            "event_type": "message",
            "session_id": hook_input.get("session_id", "unknown"),
            "session_name": hook_input.get("session_id", "unknown"),
            "timestamp": datetime.now(UTC).isoformat(),
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
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
