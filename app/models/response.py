from pydantic import BaseModel
from typing import List, Optional


class ChatMessageResponse(BaseModel):
    content: str
    session_id: str


class MessageResponse(BaseModel):
    content: str
    type: str
    timestamp: str  # ISO 8601 형식의 문자열 2024-11-21T20:13:25.684685"


class ChatHistoryResponse(BaseModel):
    messages: List[MessageResponse]
    cursor: Optional[str] = None  # Optional cursor for pagination, if applicable

