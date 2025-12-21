"""SSE Connection Manager (ADR-013)

Manages Server-Sent Events connections for real-time session streaming.
Provides the same events as WebSocket but with standard HTTP benefits.
"""

from dataclasses import dataclass, field
from typing import Optional, Union
import asyncio
import json
import time

from models import StreamEventType


@dataclass
class SSEConnection:
    """Represents an active SSE connection."""
    connection_id: str
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    session_id_filter: Optional[str] = None  # Filter to single session
    created_by_filter: Optional[str] = None  # Filter by creator (future auth)


class SSEManager:
    """Manages SSE connections and event broadcasting."""

    def __init__(self):
        self._connections: dict[str, SSEConnection] = {}
        self._sequence: dict[int, int] = {}
        self._sequence_lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        """Return number of active SSE connections."""
        return len(self._connections)

    def register(self, connection: SSEConnection) -> None:
        """Register a new SSE connection."""
        self._connections[connection.connection_id] = connection

    def unregister(self, connection_id: str) -> None:
        """Unregister an SSE connection."""
        self._connections.pop(connection_id, None)

    def clear_all(self) -> None:
        """Clear all connections (for shutdown)."""
        self._connections.clear()

    async def generate_event_id(self, event_type: StreamEventType) -> str:
        """Generate unique event ID: <timestamp_ms>-<type_abbrev>-<sequence>."""
        async with self._sequence_lock:
            ts_ms = int(time.time() * 1000)
            seq = self._sequence.get(ts_ms, 0) + 1
            self._sequence[ts_ms] = seq
            # Cleanup old timestamps (keep last second only)
            self._sequence.clear()
            self._sequence[ts_ms] = seq

        return f"{ts_ms}-{event_type.abbrev}-{seq:03d}"

    @staticmethod
    def format_event(event_id: str, event_type: StreamEventType, data: dict) -> str:
        """Format an SSE event with id, event type, and JSON data."""
        return f"id: {event_id}\nevent: {event_type.value}\ndata: {json.dumps(data)}\n\n"

    async def broadcast(
        self,
        event_type: StreamEventType,
        data: dict,
        session_id: Optional[str] = None,
    ) -> int:
        """Broadcast event to all SSE connections (with filtering).

        Args:
            event_type: The SSE event type
            data: The event data to send as JSON
            session_id: The session this event relates to (for filtering)

        Returns:
            Number of connections the event was sent to
        """
        if not self._connections:
            return 0

        event_id = await self.generate_event_id(event_type)
        message = self.format_event(event_id, event_type, data)
        sent_count = 0

        for conn in list(self._connections.values()):
            # Apply session filter
            if conn.session_id_filter and session_id and conn.session_id_filter != session_id:
                continue

            try:
                await conn.queue.put(message)
                sent_count += 1
            except Exception:
                # Connection may have been removed, ignore
                pass

        return sent_count


# Global SSE manager instance
sse_manager = SSEManager()
