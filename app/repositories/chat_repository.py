import time
from typing import List, Dict, Any, Optional

from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.db import get_dynamodb_resource
from app.models.chat import SessionMetadata, ActiveSession


class ChatRepository:
    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
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
            self, user_id: str, session_id: str, created_at: int, active_session_ttl_seconds: int
    ) -> Optional[ActiveSession]:
        """새 활성 세션 생성 (TTL 설정)"""

        item = {
            'user_id': user_id,
            'session_id': session_id,
            'created_at': created_at,
            'updated_at': created_at,
            'expired_at': created_at + active_session_ttl_seconds
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

    def update_active_session_ttl(self, user_id: str, session_id: str, current_time_s: int,
                                  active_session_ttl_seconds: int):
        """활성 세션의 TTL 갱신"""
        try:
            self.active_session_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET updated_at = :u_val, expired_at = :e_val",
                ConditionExpression="session_id = :sid_val",  # 해당 session_id가 일치할 때만 업데이트
                ExpressionAttributeValues={
                    ':sid_val': session_id,
                    ':u_val': current_time_s,
                    ':e_val': current_time_s + active_session_ttl_seconds
                }
            )
        except ClientError as e:
            print(f"Error updating active session TTL: {e}")
            raise

    def create_session_metadata(self, user_id: str, session_id: str, created_at: int) -> SessionMetadata:
        """세션 메타데이터 생성"""

        item = {
            'user_id': user_id,
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

    def get_sessions_by_user_id(self, user_id: str) -> List[SessionMetadata]:
        """사용자 ID로 세션 메타데이터 조회"""
        try:
            response = self.session_metadata_table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id}
            )
            return [SessionMetadata(**item) for item in response.get('Items', [])]
        except ClientError as e:
            print(f"Error getting sessions for user {user_id}: {e}")
            raise

    def get_messages_by_session_id(self, session_id: str) -> List[str]:
        """세션 ID로 메시지 조회"""
        try:
            response = self.langchainTable.get_item(
                Key={'session_id': session_id}
            )
            history = response['Item']['History']
            return [convert_history_item_to_chat(item) for item in history]
        except ClientError as e:
            print(f"Error getting messages for session {session_id}: {e}")
            raise


def convert_history_item_to_chat(item: Dict[str, Any]) -> str:
    """
    Convert a history item from DynamoDB format to a chat message string.
    """
    if 'data' in item and 'content' in item['data']:
        return f"{item['type']}: {item['data']['content']}"
    return ""

