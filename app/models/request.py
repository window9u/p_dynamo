from pydantic import BaseModel
from typing import List, Optional


class SendMessageRequest(BaseModel):
    user_id: str
    content: str


class ChatMessageResponse(BaseModel):
    content: str
    session_id: str


class ChatHistoryResponse(BaseModel):
    messages: List[str]


class SessionInfoResponse(BaseModel):
    session_id: str
    session_summary: Optional[str]
    created_at: int
    finished_at: Optional[int]
    