from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from app.models.request import SendMessageRequest
from app.models.response import ChatHistoryResponse, ChatMessageResponse
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
        return await chat_service.handle_user_message(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    user_id: str,
    cursor: Optional[str] = Query(default=None, description="커서 기반 페이지네이션을 위한 커서 값"),
    limit: int = Query(default=4, gt=0, le=100, description="반환할 채팅 기록의 최대 개수 (1-100)"),
    chat_service: ChatService = Depends(get_chat_service)
):
    """세션 ID에 해당하는 채팅 기록을 가져옵니다."""
    try:
        return chat_service.get_user_history(user_id, cursor, limit)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
