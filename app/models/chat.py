from pydantic import BaseModel, Field
from typing import Optional, List


class SessionMetadata(BaseModel):
    user_id: str  # partition key
    sort_key: str  # session_id#created_at
    session_id: str  # uuid
    session_summary: Optional[str] = None
    created_at: int  # Number
    finished_at: Optional[int] = None  # Number


class ActiveSession(BaseModel):
    user_id: str  # partition key
    session_id: str
    created_at: int  # Number
    ttl_expiry: int  # Number


class LangChainSession(BaseModel):
    SessionId: str  # partition key
    history: List
