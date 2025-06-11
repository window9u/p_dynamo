import time
import uuid
from typing import List, Dict, Any

from app.repositories.chat_repository import ChatRepository
from app.models.chat import ChatMessage # 필요한 경우 모델을 가져와서 사용할 수 있음

class ChatService:
    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo
        self.active_session_ttl_seconds = 60 

    async def get_or_create_session(self, user_id: str) -> str:
        """
        사용자의 활성 세션을 가져오거나 새로 생성합니다.
        """
        active_session = self.chat_repo.get_active_session(user_id)

        if active_session:
            session_id = active_session['session_id']
            # 기존 세션 TTL 갱신
            self.chat_repo.update_active_session_ttl(user_id, session_id, self.active_session_ttl_seconds)
            print(f"Existing active session found for user {user_id}: {session_id}")
            return session_id
        else:
            # 새 세션 생성
            new_session_id = str(uuid.uuid4())
            created_session = self.chat_repo.create_active_session(user_id, new_session_id, self.active_session_ttl_seconds)
            
            if created_session:
                # Session Metadata도 함께 생성
                self.chat_repo.create_session_metadata(user_id, new_session_id)
                print(f"New active session created for user {user_id}: {new_session_id}")
                return new_session_id
            else:
                # 동시 요청 등으로 인해 이미 생성되었을 경우, 다시 조회
                # (이런 케이스는 극히 드물지만, 견고성을 위해)
                active_session_after_retry = self.chat_repo.get_active_session(user_id)
                if active_session_after_retry:
                    print(f"Race condition: Active session for user {user_id} was created by another request. Using existing: {active_session_after_retry['session_id']}")
                    return active_session_after_retry['session_id']
                else:
                    raise Exception("Failed to get or create active session.")


    async def handle_user_message(self, user_id: str, content: str) -> List[Dict[str, Any]]:
        """
        사용자 메시지를 처리하고, AI 응답을 생성하며, 메시지를 저장합니다.
        """
        session_id = await self.get_or_create_session(user_id)

        # 1. 사용자 메시지 저장
        user_message_item = self.chat_repo.add_chat_message(session_id, user_id, 'user', content)
        print(f"User message saved: {user_message_item['message_id']}")

        # 2. AI 챗봇 응답 생성 (여기에 AI 모델 호출 로직 추가)
        # 예시: 간단한 Echo 봇
        ai_response_content = f"Echo from AI: {content}" 
        # 실제 AI 모델 통합 시에는 비동기적으로 AI API를 호출해야 할 수 있습니다.

        # 3. AI 응답 저장
        ai_message_item = self.chat_repo.add_chat_message(session_id, user_id, 'ai', ai_response_content)
        print(f"AI response saved: {ai_message_item['message_id']}")

        # 4. (선택 사항) 최근 메시지 히스토리 반환 또는 전체 히스토리 반환
        # 여기서는 방금 보낸 메시지와 AI 응답만 반환하거나, 아니면 최근 N개 메시지를 반환하도록 선택
        # 여기서는 방금 저장된 메시지 두 개만 반환합니다.
        return [user_message_item, ai_message_item]

    async def get_chat_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        특정 사용자의 현재 활성 세션의 채팅 기록을 가져옵니다.
        """
        active_session = self.chat_repo.get_active_session(user_id)
        if not active_session:
            return [] # 활성 세션이 없으면 빈 목록 반환

        session_id = active_session['session_id']
        # TTL 갱신
        self.chat_repo.update_active_session_ttl(user_id, session_id, self.active_session_ttl_seconds)

        history = self.chat_repo.get_chat_history(session_id, limit=limit, scan_index_forward=False) # 최신 순
        return history

    async def end_session(self, user_id: str, session_summary: str = "No summary provided."):
        """
        세션을 종료하고, Active Session을 삭제하며, Session Metadata에 요약 저장
        """
        active_session = self.chat_repo.get_active_session(user_id)
        if not active_session:
            print(f"No active session found for user {user_id} to end.")
            return

        session_id_to_end = active_session['session_id']

        # Session Metadata에 요약 업데이트
        # Session Metadata의 PK/SK를 알아야 하므로, Session Metadata에서 session_id로 created_at을 조회해야 함
        # 현재 Session Metadata에는 session_id를 PK로 하는 GSI가 없으므로, user_id와 session_id가 매칭되는 항목을 찾아야 함.
        # 이 부분은 GSI가 필요하거나, Active Session에 created_at을 추가하는 것이 더 효율적일 수 있습니다.
        # 임시 방편으로 모든 세션을 가져와서 필터링 (비효율적)
        user_sessions = self.chat_repo.get_user_sessions_metadata(user_id)
        target_session = next((s for s in user_sessions if s['session_id'] == session_id_to_end), None)

        if target_session:
            self.chat_repo.update_session_metadata_summary(
                user_id, 
                session_id_to_end, 
                target_session['created_at'], 
                session_summary
            )
            print(f"Session metadata updated for session {session_id_to_end}.")
        else:
            print(f"Warning: Session metadata not found for session {session_id_to_end}.")

        # Active Session 삭제
        self.chat_repo.delete_active_session(user_id)
        print(f"Active session {session_id_to_end} for user {user_id} ended.")