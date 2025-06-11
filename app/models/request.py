from pydantic import BaseModel
from typing import List, Optional

class SendMessageRequest(BaseModel):
    user_id: str
    content: str

class ChatMessageResponse(BaseModel):
    user_id: str
    message_id: str
    timestamp: int
    content: str
    sender_type: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageResponse]

class SessionInfoResponse(BaseModel):
    session_id: str
    session_summary: Optional[str]
    created_at: int
    finished_at: Optional[int]
    