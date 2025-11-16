from pydantic import BaseModel
from typing import Optional

class Event(BaseModel):
    """Event model for hook data"""
    event_type: str  # 'session_start' | 'pre_tool'
    session_id: str
    session_name: str
    timestamp: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
