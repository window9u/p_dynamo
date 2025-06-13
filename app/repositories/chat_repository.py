import time
import uuid
import uuid6  # pip install uuid6
from typing import List, Dict, Any, Optional

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.db import get_dynamodb_resource
from app.models.chat import SessionMetadata, ActiveSession


def _generate_sort_key(timestamp_ms: int, session_id: str) -> str:
    return f"{session_id}#{timestamp_ms}"


class ChatRepository:
    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.chat_messages_table = self.dynamodb.Table(settings.DYNAMODB_CHAT_MESSAGES_TABLE)
        self.session_metadata_table = self.dynamodb.Table(settings.DYNAMODB_SESSION_METADATA_TABLE)
        self.active_session_table = self.dynamodb.Table(settings.DYNAMODB_ACTIVE_SESSION_TABLE)
        self.langchainTable = self.dynamodb.Table(settings.DYNAMODB_LANGCHAIN_TABLE)

    def get_active_session(self, user_id: str) -> Optional[ActiveSession]:
        """사용자의 현재 활성 세션 조회"""
        try:
            response = self.active_session_table.get_item(Key={'user_id': user_id})
            if 'Item' not in response:
                return None
            # 반환된 아이템을 ActiveSession 모델로 변환
            return ActiveSession(**response['Item'])
        except ClientError as e:
            print(f"Error getting active session: {e}")
            raise

    def create_active_session(
            self, user_id: str, session_id: str, created_at: int, ttl_expiry_add: int
    ) -> Optional[ActiveSession]:
        """새 활성 세션 생성 (TTL 설정)"""
        current_time_s = int(time.time())
        ttl_expiry = current_time_s + ttl_expiry_add

        item = {
            'user_id': user_id,
            'session_id': session_id,
            'created_at': created_at,
            'ttl_expiry': ttl_expiry
        }
        try:
            # 조건부 쓰기: user_id가 없어야만 생성
            self.active_session_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(user_id)'
            )
            return ActiveSession(**item)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Active session for user {user_id} already exists.")
                return None  # 이미 존재하면 None 반환
            print(f"Error creating active session: {e}")
            raise

    def update_active_session_ttl(self, user_id: str, session_id: str, ttl_expiry_seconds: int):
        """활성 세션의 TTL 갱신"""
        current_time_s = int(time.time())
        new_ttl_expiry = current_time_s + ttl_expiry_seconds
        try:
            self.active_session_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET ttl_expiry = :val",
                ConditionExpression="session_id = :sid_val",  # 해당 session_id가 일치할 때만 업데이트
                ExpressionAttributeValues={':val': new_ttl_expiry, ':sid_val': session_id}
            )
        except ClientError as e:
            print(f"Error updating active session TTL: {e}")
            raise

    def delete_active_session(self, user_id: str):
        """활성 세션 삭제 (예: 대화 종료 시)"""
        try:
            self.active_session_table.delete_item(Key={'user_id': user_id})
        except ClientError as e:
            print(f"Error deleting active session: {e}")
            raise

    def create_session_metadata(self, user_id: str, session_id: str, created_at: int) -> SessionMetadata:
        """세션 메타데이터 생성"""
        sort_key = _generate_sort_key(created_at, session_id)

        item = {
            'user_id': user_id,
            'sort_key': sort_key,
            'session_id': session_id,
            'created_at': created_at,
            'session_summary': 'session not finished yet',  # 세션이 끝나지 않았으므로 초기값 설정
        }
        try:
            self.session_metadata_table.put_item(Item=item)
            return SessionMetadata(**item)
        except ClientError as e:
            print(f"Error creating session metadata: {e}")
            raise
