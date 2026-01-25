"""
Thread-safe queue for script sync commands with async event signaling.

Manages pending script sync/remove commands per runner with asyncio Events
for immediate wake-up of long-polling runners when a sync command is queued.
"""

import asyncio
import threading
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class RunnerScriptSyncState:
    """Script sync commands and event for a single runner."""
    sync_scripts: set[str] = field(default_factory=set)  # script names to sync
    remove_scripts: set[str] = field(default_factory=set)  # script names to remove
    event: asyncio.Event = field(default_factory=asyncio.Event)


class ScriptSyncQueue:
    """Thread-safe queue for script sync commands with async event signaling."""

    def __init__(self):
        self._runners: dict[str, RunnerScriptSyncState] = {}
        self._lock = threading.Lock()

    def register_runner(self, runner_id: str) -> None:
        """Register a runner and create its event."""
        with self._lock:
            if runner_id not in self._runners:
                self._runners[runner_id] = RunnerScriptSyncState(
                    event=asyncio.Event()
                )

    def unregister_runner(self, runner_id: str) -> None:
        """Remove runner state when deregistered."""
        with self._lock:
            self._runners.pop(runner_id, None)

    def add_sync(self, runner_id: str, script_name: str) -> bool:
        """Queue a script sync command and wake up the runner's poll.

        Returns True if command was queued, False if runner not found.
        """
        with self._lock:
            state = self._runners.get(runner_id)
            if not state:
                return False

            # If script was marked for removal, cancel that
            state.remove_scripts.discard(script_name)
            state.sync_scripts.add(script_name)
            state.event.set()  # Wake up the poll!
            return True

    def add_remove(self, runner_id: str, script_name: str) -> bool:
        """Queue a script remove command and wake up the runner's poll.

        Returns True if command was queued, False if runner not found.
        """
        with self._lock:
            state = self._runners.get(runner_id)
            if not state:
                return False

            # If script was marked for sync, cancel that
            state.sync_scripts.discard(script_name)
            state.remove_scripts.add(script_name)
            state.event.set()  # Wake up the poll!
            return True

    def add_sync_all_runners(self, script_name: str) -> int:
        """Queue a script sync command for all registered runners.

        Returns count of runners that received the command.
        """
        count = 0
        with self._lock:
            for state in self._runners.values():
                state.remove_scripts.discard(script_name)
                state.sync_scripts.add(script_name)
                state.event.set()
                count += 1
        return count

    def add_remove_all_runners(self, script_name: str) -> int:
        """Queue a script remove command for all registered runners.

        Returns count of runners that received the command.
        """
        count = 0
        with self._lock:
            for state in self._runners.values():
                state.sync_scripts.discard(script_name)
                state.remove_scripts.add(script_name)
                state.event.set()
                count += 1
        return count

    def get_and_clear(self, runner_id: str) -> tuple[list[str], list[str]]:
        """Get pending script commands and clear them.

        Returns tuple of (sync_scripts, remove_scripts).
        """
        with self._lock:
            state = self._runners.get(runner_id)
            if not state:
                return [], []

            sync = list(state.sync_scripts)
            remove = list(state.remove_scripts)
            state.sync_scripts.clear()
            state.remove_scripts.clear()
            state.event.clear()
            return sync, remove

    def has_pending(self, runner_id: str) -> bool:
        """Check if runner has pending script commands."""
        with self._lock:
            state = self._runners.get(runner_id)
            if not state:
                return False
            return bool(state.sync_scripts or state.remove_scripts)

    def get_event(self, runner_id: str) -> Optional[asyncio.Event]:
        """Get the asyncio Event for a runner (for poll wait)."""
        with self._lock:
            state = self._runners.get(runner_id)
            return state.event if state else None


# Module-level singleton
script_sync_queue = ScriptSyncQueue()
