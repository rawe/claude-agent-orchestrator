"""
Launcher registry for tracking registered launcher instances.

Launchers register on startup and send periodic heartbeats to stay alive.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel


class LauncherInfo(BaseModel):
    """Information about a registered launcher."""
    launcher_id: str
    registered_at: str
    last_heartbeat: str
    # Metadata provided by the launcher
    hostname: Optional[str] = None
    project_dir: Optional[str] = None


class LauncherRegistry:
    """Thread-safe registry for tracking launchers."""

    def __init__(self, heartbeat_timeout_seconds: int = 120):
        self._launchers: dict[str, LauncherInfo] = {}
        self._lock = threading.Lock()
        self._heartbeat_timeout = heartbeat_timeout_seconds

    def register_launcher(
        self,
        hostname: Optional[str] = None,
        project_dir: Optional[str] = None,
    ) -> LauncherInfo:
        """Register a new launcher and return its info.

        Args:
            hostname: The machine hostname where the launcher is running
            project_dir: The default project directory for this launcher
        """
        launcher_id = f"lnch_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        launcher = LauncherInfo(
            launcher_id=launcher_id,
            registered_at=now,
            last_heartbeat=now,
            hostname=hostname,
            project_dir=project_dir,
        )

        with self._lock:
            self._launchers[launcher_id] = launcher

        return launcher

    def heartbeat(self, launcher_id: str) -> bool:
        """Update last heartbeat timestamp.

        Returns True if launcher exists, False otherwise.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            launcher = self._launchers.get(launcher_id)
            if not launcher:
                return False

            launcher.last_heartbeat = now
            return True

    def get_launcher(self, launcher_id: str) -> Optional[LauncherInfo]:
        """Get launcher info by ID."""
        with self._lock:
            return self._launchers.get(launcher_id)

    def is_launcher_alive(self, launcher_id: str) -> bool:
        """Check if launcher is registered and has sent a recent heartbeat."""
        with self._lock:
            launcher = self._launchers.get(launcher_id)
            if not launcher:
                return False

            # Check if heartbeat is within timeout
            last_hb = datetime.fromisoformat(launcher.last_heartbeat.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            seconds_since_heartbeat = (now - last_hb).total_seconds()

            return seconds_since_heartbeat < self._heartbeat_timeout

    def get_all_launchers(self) -> list[LauncherInfo]:
        """Get all registered launchers."""
        with self._lock:
            return list(self._launchers.values())

    def remove_launcher(self, launcher_id: str) -> bool:
        """Remove a launcher from the registry.

        Returns True if launcher was removed, False if not found.
        """
        with self._lock:
            if launcher_id in self._launchers:
                del self._launchers[launcher_id]
                return True
            return False


# Module-level singleton
launcher_registry = LauncherRegistry()
