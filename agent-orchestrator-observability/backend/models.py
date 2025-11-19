from pydantic import BaseModel
from typing import Optional, Any, List

class SessionMetadataUpdate(BaseModel):
    """Model for updating session metadata"""
    session_name: Optional[str] = None
    project_dir: Optional[str] = None

class MessageContent(BaseModel):
    """Content block within a message"""
    type: str  # 'text' (only text supported for now)
    text: str

class Event(BaseModel):
    """Event model for hook data"""
    event_type: str  # 'session_start' | 'pre_tool' | 'post_tool' | 'session_stop' | 'message'
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
    # Message fields
    role: Optional[str] = None  # 'assistant' | 'user'
    content: Optional[List[dict]] = None  # Array of content blocks
