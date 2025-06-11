from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from app.models.request import SendMessageRequest, ChatMessageResponse, ChatHistoryResponse, SessionInfoResponse
from app.services.chat_service import ChatService
from app.repositories.chat_repository import ChatRepository # ChatService 초기화용

router = APIRouter()

# 의존성 주입 (Dependency Injection)
def get_chat_service(repo: ChatRepository = Depends(ChatRepository)) -> ChatService:
    return ChatService(repo)

@router.post("/send_message", response_model=List[ChatMessageResponse])
async def send_message(
    request: SendMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """사용자 메시지를 보내고 AI 응답을 받습니다."""
    try:
        messages = await chat_service.handle_user_message(request.user_id, request.content)
        # 응답 모델에 맞게 변환
        return [ChatMessageResponse(**msg) for msg in messages]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    user_id: str,
    limit: int = 20,
    chat_service: ChatService = Depends(get_chat_service)
):
    """특정 사용자의 현재 활성 세션 채팅 기록을 가져옵니다."""
    try:
        messages = await chat_service.get_chat_history(user_id, limit)
        if not messages:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session or chat history found.")
        
        session_id = messages[0]['session_id'] # 첫 번째 메시지에서 세션 ID 가져오기 (모든 메시지는 같은 세션 ID)
        return ChatHistoryResponse(session_id=session_id, messages=[ChatMessageResponse(**msg) for msg in messages])
    except HTTPException: # 이미 HTTPException 발생한 경우 그대로 전달
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/end_session/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(
    user_id: str,
    summary: Optional[str] = "No summary provided.",
    chat_service: ChatService = Depends(get_chat_service)
):
    """사용자의 현재 활성 세션을 종료합니다."""
    try:
        await chat_service.end_session(user_id, summary)
        return {"message": "Session ended successfully."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))