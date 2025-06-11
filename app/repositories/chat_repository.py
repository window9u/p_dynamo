import time
import uuid
import uuid6 # pip install uuid6
from typing import List, Dict, Any, Optional

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.db import get_dynamodb_resource

class ChatRepository:
    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.chat_messages_table = self.dynamodb.Table(settings.DYNAMODB_CHAT_MESSAGES_TABLE)
        self.session_metadata_table = self.dynamodb.Table(settings.DYNAMODB_SESSION_METADATA_TABLE)
        self.active_session_table = self.dynamodb.Table(settings.DYNAMODB_ACTIVE_SESSION_TABLE)

    def _generate_sort_key(self, timestamp_ms: int, message_id: str) -> str:
        return f"{timestamp_ms}#{message_id}"

    def _generate_session_sort_key(self, timestamp_ms: int, session_id: str) -> str:
        return f"{timestamp_ms}#{session_id}"

    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자의 현재 활성 세션 조회"""
        try:
            response = self.active_session_table.get_item(Key={'user_id': user_id})
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting active session: {e}")
            raise

    def create_active_session(self, user_id: str, session_id: str, ttl_expiry_seconds: int) -> Dict[str, Any]:
        """새 활성 세션 생성 (TTL 설정)"""
        current_time_s = int(time.time())
        ttl_expiry = current_time_s + ttl_expiry_seconds
        
        item = {
            'user_id': user_id,
            'session_id': session_id,
            'ttl_expiry': ttl_expiry
        }
        try:
            # 조건부 쓰기: user_id가 없어야만 생성
            self.active_session_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(user_id)'
            )
            return item
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Active session for user {user_id} already exists.")
                return None # 이미 존재하면 None 반환
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
                ExpressionAttributeValues={':val': new_ttl_expiry},
                ConditionExpression="session_id = :sid_val", # 해당 session_id가 일치할 때만 업데이트
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

    def add_chat_message(self, session_id: str, user_id: str, sender_type: str, content: str) -> Dict[str, Any]:
        """채팅 메시지 추가"""
        current_time_ms = int(time.time() * 1000)
        message_id = str(uuid.uuid4()) # 또는 uuid6.uuid6()
        sort_key = self._generate_sort_key(current_time_ms, message_id)

        item = {
            'session_id': session_id,
            'sort_key': sort_key,
            'user_id': user_id,
            'message_id': message_id,
            'timestamp': current_time_ms,
            'content': content,
            'sender_type': sender_type
        }
        try:
            self.chat_messages_table.put_item(Item=item)
            return item
        except ClientError as e:
            print(f"Error adding chat message: {e}")
            raise

    def get_chat_history(self, session_id: str, limit: int = 20, scan_index_forward: bool = False) -> List[Dict[str, Any]]:
        """특정 세션의 채팅 기록 조회"""
        try:
            response = self.chat_messages_table.query(
                KeyConditionExpression=Key('session_id').eq(session_id),
                Limit=limit,
                ScanIndexForward=scan_index_forward # True: 오래된 순, False: 최신 순
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting chat history: {e}")
            raise

    def create_session_metadata(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """세션 메타데이터 생성"""
        current_time_ms = int(time.time() * 1000)
        sort_key = self._generate_session_sort_key(current_time_ms, session_id)
        
        item = {
            'user_id': user_id,
            'sort_key': sort_key,
            'session_id': session_id,
            'created_at': current_time_ms,
            # 'session_summary': 'Initial summary' (선택 사항)
        }
        try:
            self.session_metadata_table.put_item(Item=item)
            return item
        except ClientError as e:
            print(f"Error creating session metadata: {e}")
            raise

    def update_session_metadata_summary(self, user_id: str, session_id: str, created_at_ms: int, summary: str):
        """세션 요약 업데이트 (세션 종료 시 호출)"""
        sort_key = self._generate_session_sort_key(created_at_ms, session_id)
        try:
            self.session_metadata_table.update_item(
                Key={'user_id': user_id, 'sort_key': sort_key},
                UpdateExpression="SET session_summary = :s, finished_at = :f",
                ExpressionAttributeValues={
                    ':s': summary,
                    ':f': int(time.time() * 1000)
                }
            )
        except ClientError as e:
            print(f"Error updating session metadata summary: {e}")
            raise
            
    def get_user_sessions_metadata(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """사용자의 모든 세션 메타데이터 조회"""
        try:
            response = self.session_metadata_table.query(
                KeyConditionExpression=Key('user_id').eq(user_id),
                Limit=limit,
                ScanIndexForward=False # 최신 세션부터
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting user sessions metadata: {e}")
            raise