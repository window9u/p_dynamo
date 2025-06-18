import time
import boto3  # AWS SDK - 표준 라이브러리는 아니지만 매우 일반적이고 널리 사용됨

from uuid_extensions import uuid7  # 외부 라이브러리
from langchain_community.chat_message_histories import (  # 외부 라이브러리
    DynamoDBChatMessageHistory,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # 외부 라이브러리
from langchain_core.runnables.history import RunnableWithMessageHistory  # 외부 라이브러리
from langchain_openai import ChatOpenAI  # 외부 라이브러리

from app.repositories.chat_repository import ChatRepository  # 내부 모듈
from app.core.config import settings  # 내부 모듈
from app.models.entity import Message, SenderType  # 내부 모듈
from app.models.request import SendMessageRequest
from app.models.response import ChatHistoryResponse, ChatMessageResponse, MessageResponse

dynamodb = boto3.resource("dynamodb")
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)

chain = prompt | ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini", temperature=0.7)


class ChatService:
    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo
        self.active_session_ttl_seconds = settings.ACTIVE_SESSION_TTL_SECONDS
        self.token_limit_per_session = settings.TOKEN_LIMIT_PER_SESSION
        self.chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda sid: DynamoDBChatMessageHistory(
                table_name=settings.DYNAMODB_LANGCHAIN_TABLE, session_id=sid, primary_key_name="session_id"
            ),
            input_messages_key="question",
            history_messages_key="history",
        )

    async def upsert_active_session(self, user_id: str, current_time_s: int) -> str:
        """
        사용자의 활성 세션을 가져오거나 새로 생성합니다.
        """
        active_session = self.chat_repo.get_active_session(user_id)

        if active_session and active_session.token_usage <= self.token_limit_per_session:  # 이미 활성 세션이 있는 경우
            self.chat_repo.update_active_session_ttl(
                user_id, active_session.session_id,
                current_time_s,
                self.active_session_ttl_seconds
            )
            print(f"Existing active session found for user {user_id}: {active_session.session_id}")
            print(active_session.token_usage, self.token_limit_per_session)
            return active_session.session_id

        if active_session and active_session.token_usage >= self.token_limit_per_session:
            print(f"Active session for user {user_id} has reached token usage limit.")
            self.chat_repo.remove_active_session(user_id)

        new_session_id = str(uuid7())
        self.chat_repo.create_active_session(
            user_id,
            new_session_id,
            current_time_s,
            self.active_session_ttl_seconds,
        )

        # Session Metadata도 함께 생성
        self.chat_repo.create_session_metadata(user_id, new_session_id, current_time_s)
        print(f"New active session created for user {user_id}: {new_session_id}")
        return new_session_id

    async def handle_user_message(self, request: SendMessageRequest) -> ChatMessageResponse:
        """
        사용자 메시지를 처리하고, AI 응답을 생성하며, 메시지를 저장합니다.
        """
        # 0. 유저별 토큰 상태 체크
        # TODO(window9u): 유저별 토큰 사용량 체크 로직 추가, Relation Database 사용

        # 1. 사용자의 활성 세션을 가져오거나 새로 생성
        current_time_s = int(time.time())

        session_id = await self.upsert_active_session(request.user_id, current_time_s)

        self.chat_repo.put_message(
            Message(
                user_id=request.user_id,
                sort_key=f"{session_id}#{current_time_s}",
                session_id=session_id,
                content=request.content,
                sender_type=SenderType.HUMAN,
                created_at=current_time_s,
            )
        )

        config = {"configurable": {"session_id": session_id}}
        llm_response = self.chain_with_history.invoke(
            input={
                "question": request.content,
                "history": self.chat_repo.get_current_session_metadata_by_user_id(
                    request.user_id,
                    settings.SESSION_SUMMARY_WINDOW  # 항상 최신 SESSION_SUMMARY_WINDOW 개의 세션 요약을 가져옴
                )
            },
            config=config
        )

        ai_response_time_s = int(time.time()) + 1  # AI 응답 시간은 현재 시간 + 1초로 설정
        self.chat_repo.put_message(
            Message(
                user_id=request.user_id,
                sort_key=f"{session_id}#{ai_response_time_s}",
                session_id=session_id,
                content=llm_response.content,
                sender_type=SenderType.AI,
                created_at=ai_response_time_s,
            )
        )

        self.chat_repo.update_active_session_token_usage(request.user_id, llm_response.usage_metadata['total_tokens'])
        # TODO(window9u): 유저별 토큰 사용량 업데이트

        return ChatMessageResponse(
            content=llm_response.content,
            session_id=session_id
        )

    def get_user_history(self, user_id: str, cursor: str, limit: int) -> ChatHistoryResponse:
        """
        세션 ID에 해당하는 채팅 기록을 가져옵니다.
        """
        messages, last_evaluated_key = self.chat_repo.get_messages_of_user(user_id, cursor, limit)
        return ChatHistoryResponse(
            messages=[
                MessageResponse(
                    content=message.content,
                    type=message.sender_type,
                    timestamp=_convert_num_to_ISO8601(message.created_at),
                )
                for message in messages
            ],
            cursor=last_evaluated_key if last_evaluated_key else None
        )


def _convert_num_to_ISO8601(num: int) -> str:
    """
    Convert a Unix timestamp to ISO 8601 format.
    """
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(num)) + 'Z'  # 'Z' indicates UTC time
