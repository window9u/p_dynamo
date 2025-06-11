from pydantic import BaseModel, Field
from typing import Optional

class ChatMessage(BaseModel):
    session_id: str # partition key
    sort_key: str # timestamp#message_id
    user_id: str
    message_id: str
    timestamp: int # Number
    content: str
    sender_type: str # 'user' or 'ai'

class SessionMetadata(BaseModel):
    user_id: str # partition key
    sort_key: str # created_at#session_id
    session_id: str
    session_summary: Optional[str] = None
    created_at: int # Number
    finished_at: Optional[int] = None # Number

class ActiveSession(BaseModel):
    user_id: str # partition key
    ttl_expiry: int # Number
    session_id: str
