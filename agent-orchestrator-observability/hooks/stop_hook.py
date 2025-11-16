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

        # Extract last message from transcript file
        transcript_path = hook_input.get("transcript_path")
        last_message = None

        if transcript_path:
            try:
                with open(transcript_path, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1]
                        transcript_entry = json.loads(last_line)

                        # Extract message if it exists
                        if "message" in transcript_entry:
                            msg = transcript_entry["message"]
                            last_message = {
                                "role": msg.get("role"),
                                "content": msg.get("content", [])
                            }
            except Exception:
                # If we can't read the transcript, continue without the message
                pass

        # Send session_stop event
        backend_url = "http://localhost:8765/events"

        session_stop_event = {
            "event_type": "session_stop",
            "session_id": hook_input.get("session_id", "unknown"),
            "session_name": hook_input.get("session_id", "unknown"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            httpx.post(backend_url, json=session_stop_event, timeout=2.0)
        except Exception:
            pass

        # Send message event if we extracted one
        if last_message and last_message.get("role") and last_message.get("content"):
            message_event = {
                "event_type": "message",
                "session_id": hook_input.get("session_id", "unknown"),
                "session_name": hook_input.get("session_id", "unknown"),
                "timestamp": datetime.now(UTC).isoformat(),
                "role": last_message["role"],
                "content": last_message["content"]
            }

            try:
                httpx.post(backend_url, json=message_event, timeout=2.0)
            except Exception:
                pass

    except Exception:
        # Fail silently - hooks should never crash the agent
        pass

    # Always exit successfully
    sys.exit(0)

if __name__ == "__main__":
    main()
