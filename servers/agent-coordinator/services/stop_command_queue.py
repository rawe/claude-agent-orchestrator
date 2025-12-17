"""
Thread-safe queue for stop commands with async event signaling.

Manages pending stop commands per runner with asyncio Events for immediate wake-up
of long-polling runners when a stop command is queued.
"""

import asyncio
import threading
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class RunnerStopState:
    """Stop commands and event for a single runner."""
    pending_stops: set[str] = field(default_factory=set)  # run_ids
    event: asyncio.Event = field(default_factory=asyncio.Event)


class StopCommandQueue:
    """Thread-safe queue for stop commands with async event signaling."""

    def __init__(self):
        self._runners: dict[str, RunnerStopState] = {}
        self._lock = threading.Lock()

    def register_runner(self, runner_id: str) -> None:
        """Register a runner and create its event."""
        with self._lock:
            if runner_id not in self._runners:
                self._runners[runner_id] = RunnerStopState(
                    event=asyncio.Event()
                )

    def unregister_runner(self, runner_id: str) -> None:
        """Remove runner state when deregistered."""
        with self._lock:
            self._runners.pop(runner_id, None)

    def add_stop(self, runner_id: str, run_id: str) -> bool:
        """Queue a stop command and wake up the runner's poll.

        Returns True if command was queued, False if runner not found.
        """
        with self._lock:
            state = self._runners.get(runner_id)
            if not state:
                return False

            state.pending_stops.add(run_id)
            state.event.set()  # Wake up the poll!
            return True

    def get_and_clear(self, runner_id: str) -> list[str]:
        """Get pending stop commands and clear them.

        Returns list of run_ids to stop.
        """
        with self._lock:
            state = self._runners.get(runner_id)
            if not state:
                return []

            stops = list(state.pending_stops)
            state.pending_stops.clear()
            state.event.clear()
            return stops

    def get_event(self, runner_id: str) -> Optional[asyncio.Event]:
        """Get the asyncio Event for a runner (for poll wait)."""
        with self._lock:
            state = self._runners.get(runner_id)
            return state.event if state else None


# Module-level singleton
stop_command_queue = StopCommandQueue()
