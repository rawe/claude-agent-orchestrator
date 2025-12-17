"""
Thread-safe queue for stop commands with async event signaling.

Manages pending stop commands per launcher with asyncio Events for immediate wake-up
of long-polling launchers when a stop command is queued.
"""

import asyncio
import threading
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class LauncherStopState:
    """Stop commands and event for a single launcher."""
    pending_stops: set[str] = field(default_factory=set)  # run_ids
    event: asyncio.Event = field(default_factory=asyncio.Event)


class StopCommandQueue:
    """Thread-safe queue for stop commands with async event signaling."""

    def __init__(self):
        self._launchers: dict[str, LauncherStopState] = {}
        self._lock = threading.Lock()

    def register_launcher(self, launcher_id: str) -> None:
        """Register a launcher and create its event."""
        with self._lock:
            if launcher_id not in self._launchers:
                self._launchers[launcher_id] = LauncherStopState(
                    event=asyncio.Event()
                )

    def unregister_launcher(self, launcher_id: str) -> None:
        """Remove launcher state when deregistered."""
        with self._lock:
            self._launchers.pop(launcher_id, None)

    def add_stop(self, launcher_id: str, run_id: str) -> bool:
        """Queue a stop command and wake up the launcher's poll.

        Returns True if command was queued, False if launcher not found.
        """
        with self._lock:
            state = self._launchers.get(launcher_id)
            if not state:
                return False

            state.pending_stops.add(run_id)
            state.event.set()  # Wake up the poll!
            return True

    def get_and_clear(self, launcher_id: str) -> list[str]:
        """Get pending stop commands and clear them.

        Returns list of run_ids to stop.
        """
        with self._lock:
            state = self._launchers.get(launcher_id)
            if not state:
                return []

            stops = list(state.pending_stops)
            state.pending_stops.clear()
            state.event.clear()
            return stops

    def get_event(self, launcher_id: str) -> Optional[asyncio.Event]:
        """Get the asyncio Event for a launcher (for poll wait)."""
        with self._lock:
            state = self._launchers.get(launcher_id)
            return state.event if state else None


# Module-level singleton
stop_command_queue = StopCommandQueue()
