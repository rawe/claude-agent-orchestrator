from pydantic import BaseModel
from typing import Optional, Any

class Event(BaseModel):
    """Event model for hook data"""
    event_type: str  # 'session_start' | 'pre_tool' | 'post_tool' | 'session_stop'
    session_id: str
    session_name: str
    timestamp: str
    # Tool-related fields (pre_tool and post_tool)
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[Any] = None
    error: Optional[str] = None
    # Session stop fields
    exit_code: Optional[int] = None
    reason: Optional[str] = None
