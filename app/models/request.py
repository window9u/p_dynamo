from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    user_id: str
    content: str

