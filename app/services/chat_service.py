import time
import uuid
from typing import List, Dict, Any
import boto3

from app.repositories.chat_repository import ChatRepository
from langchain_community.chat_message_histories import (
    DynamoDBChatMessageHistory,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from app.core.config import settings

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
        self.chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda sid: DynamoDBChatMessageHistory(
                table_name=settings.DYNAMODB_LANGCHAIN_TABLE, session_id=sid, primary_key_name="session_id"
            ),
            input_messages_key="question",
            history_messages_key="history",
        )

    async def upsert_session(self, user_id: str) -> str:
        """
        사용자의 활성 세션을 가져오거나 새로 생성합니다.
        """
        active_session = self.chat_repo.get_active_session(user_id)
        current_time_s = int(time.time())

        if active_session:  # 이미 활성 세션이 있는 경우
            self.chat_repo.update_active_session_ttl(
                user_id, active_session.session_id,
                current_time_s,
                self.active_session_ttl_seconds
            )
            print(f"Existing active session found for user {user_id}: {active_session.session_id}")
            return active_session.session_id
        else:  # 활성 세션이 없는 경우 새로 생성
            new_session_id = str(uuid.uuid1())
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

    async def handle_user_message(self, user_id: str, content: str) -> (str, str):
        """
        사용자 메시지를 처리하고, AI 응답을 생성하며, 메시지를 저장합니다.
        """
        # 1. 사용자의 활성 세션을 가져오거나 새로 생성
        session_id = await self.upsert_session(user_id)

        config = {"configurable": {"session_id": session_id}}
        res = self.chain_with_history.invoke(input={"question": content}, config=config)

        return session_id, res.content

    def get_chat_history(self, session_id: str) -> List[str]:
        """
        세션 ID에 해당하는 채팅 기록을 가져옵니다.
        """
        return self.chat_repo.get_messages_by_session_id(session_id)
