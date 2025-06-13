from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from app.models.request import SendMessageRequest, ChatMessageResponse, ChatHistoryResponse, SessionInfoResponse
from app.services.chat_service import ChatService
from app.repositories.chat_repository import ChatRepository  # ChatService 초기화용

router = APIRouter()


# 의존성 주입 (Dependency Injection)
def get_chat_service(repo: ChatRepository = Depends(ChatRepository)) -> ChatService:
    return ChatService(repo)


@router.post("/send_message", response_model=ChatMessageResponse)
async def send_message(
        request: SendMessageRequest,
        chat_service: ChatService = Depends(get_chat_service)
):
    """사용자 메시지를 보내고 AI 응답을 받습니다."""
    try:
        ai_message = await chat_service.handle_user_message(request.user_id, request.content)
        return ChatMessageResponse(
            content=ai_message,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
