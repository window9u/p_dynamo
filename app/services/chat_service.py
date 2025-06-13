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
        self.active_session_ttl_seconds = 60
        self.chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda sid: DynamoDBChatMessageHistory(
                table_name=settings.DYNAMODB_LANGCHAIN_TABLE, session_id=sid
            ),
            input_messages_key="question",
            history_messages_key="history",
        )

    async def upsert_session(self, user_id: str) -> str:
        """
        사용자의 활성 세션을 가져오거나 새로 생성합니다.
        """
        active_session = self.chat_repo.get_active_session(user_id)

        if active_session:
            self.chat_repo.update_active_session_ttl(user_id, active_session.session_id,
                                                     self.active_session_ttl_seconds)
            print(f"Existing active session found for user {user_id}: {active_session.session_id}")
            return active_session.session_id
        else:
            # 새 세션 생성
            new_session_id = str(uuid.uuid4())
            current_time_s = int(time.time())
            created_session = self.chat_repo.create_active_session(
                user_id,
                new_session_id,
                current_time_s,
                self.active_session_ttl_seconds,
            )

            if created_session:
                # Session Metadata도 함께 생성
                self.chat_repo.create_session_metadata(user_id, new_session_id, current_time_s)
                print(f"New active session created for user {user_id}: {new_session_id}")
                return new_session_id
            else:
                # 동시 요청 등으로 인해 이미 생성되었을 경우, 다시 조회
                # (이런 케이스는 극히 드물지만, 견고성을 위해)
                active_session_after_retry = self.chat_repo.get_active_session(user_id)
                if active_session_after_retry:
                    print(
                        f"Race condition: Active session for user {user_id} was created by another request. Using existing: {active_session_after_retry['session_id']}")
                    return active_session_after_retry['session_id']
                else:
                    raise Exception("Failed to get or create active session.")

    async def handle_user_message(self, user_id: str, content: str) -> str:
        """
        사용자 메시지를 처리하고, AI 응답을 생성하며, 메시지를 저장합니다.
        """
        # 1. 사용자의 활성 세션을 가져오거나 새로 생성
        session_id = await self.upsert_session(user_id)

        config = {"configurable": {"session_id": session_id}}
        res = self.chain_with_history.invoke(input={"question": content}, config=config)
        print(f"AI response: {res}")

        return res.content
