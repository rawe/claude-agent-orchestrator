"""
Process Registry - tracks live executor processes by session.

Thread-safe storage with dual indexing:
  - Primary: session_id -> SessionProcess
  - Secondary: run_id -> session_id (reverse lookup)
"""

import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SessionProcess:
    """A live executor process serving a session."""
    process: subprocess.Popen
    session_id: str
    started_at: datetime
    persistent: bool = False
    current_run_id: Optional[str] = None


class ProcessRegistry:
    """Thread-safe registry for tracking executor processes by session.

    Primary index is session_id (one process per session).
    Secondary index maps run_id -> session_id for lookups by run.
    """

    def __init__(self):
        self._sessions: dict[str, SessionProcess] = {}
        self._run_index: dict[str, str] = {}
        self._stopping: set[str] = set()  # sessions being stopped by poller
        self._lock = threading.Lock()

    def register_session(
        self,
        session_id: str,
        process: subprocess.Popen,
        run_id: str,
        persistent: bool = False,
    ) -> None:
        """Register a new session and its first run."""
        entry = SessionProcess(
            process=process,
            session_id=session_id,
            started_at=datetime.now(),
            persistent=persistent,
            current_run_id=run_id,
        )
        with self._lock:
            self._sessions[session_id] = entry
            self._run_index[run_id] = session_id

    def get_session(self, session_id: str) -> Optional[SessionProcess]:
        """Look up a session by session_id."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_session_by_run(self, run_id: str) -> Optional[SessionProcess]:
        """Look up a session via the run index."""
        with self._lock:
            session_id = self._run_index.get(run_id)
            if session_id is None:
                return None
            return self._sessions.get(session_id)

    def swap_run(self, session_id: str, new_run_id: str) -> Optional[str]:
        """Atomically replace the current run_id for a session.

        Removes old run from index, sets new run_id, adds to index.
        Returns the old run_id, or None if session not found.
        """
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            old_run_id = entry.current_run_id
            if old_run_id is not None:
                self._run_index.pop(old_run_id, None)
            entry.current_run_id = new_run_id
            self._run_index[new_run_id] = session_id
            return old_run_id

    def clear_run(self, session_id: str) -> Optional[str]:
        """Clear the current run_id (turn complete, process stays alive).

        Returns the cleared run_id, or None if session not found.
        """
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            old_run_id = entry.current_run_id
            if old_run_id is not None:
                self._run_index.pop(old_run_id, None)
            entry.current_run_id = None
            return old_run_id

    def mark_stopping(self, session_id: str) -> None:
        """Mark a session as being stopped by the poller (dedup guard)."""
        with self._lock:
            self._stopping.add(session_id)

    def is_stopping(self, session_id: str) -> bool:
        """Check if a session is being stopped by the poller."""
        with self._lock:
            return session_id in self._stopping

    def remove_session(self, session_id: str) -> Optional[SessionProcess]:
        """Remove a session from both indexes.

        Returns the removed entry, or None if not found.
        """
        with self._lock:
            entry = self._sessions.pop(session_id, None)
            if entry is not None and entry.current_run_id is not None:
                self._run_index.pop(entry.current_run_id, None)
            self._stopping.discard(session_id)
            return entry

    def get_all_sessions(self) -> dict[str, SessionProcess]:
        """Return a copy of all sessions for safe iteration."""
        with self._lock:
            return dict(self._sessions)

    def count(self) -> int:
        """Get the number of active sessions."""
        with self._lock:
            return len(self._sessions)
