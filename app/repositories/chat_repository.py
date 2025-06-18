import time
from typing import List, Dict, Any, Optional

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from app.core.config import settings
from app.core.db import get_dynamodb_resource
from app.models.entity import SessionMetadata, ActiveSession, Message


class ChatRepository:
    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.session_metadata_table = self.dynamodb.Table(settings.DYNAMODB_SESSION_METADATA_TABLE)
        self.message_table = self.dynamodb.Table(settings.DYNAMODB_MESSAGE_TABLE)
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
            'expired_at': created_at + active_session_ttl_seconds,
            'token_usage': 0,
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

    def update_active_session_token_usage(self, user_id: str, token_usage: int):
        """활성 세션의 토큰 사용량 갱신"""
        try:
            self.active_session_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET token_usage = token_usage + :t_val",
                ExpressionAttributeValues={
                    ':t_val': token_usage
                }
            )
        except ClientError as e:
            print(f"Error updating active session token usage: {e}")
            raise

    def remove_active_session(self, user_id: str):
        """활성 세션 제거"""
        try:
            self.active_session_table.delete_item(
                Key={'user_id': user_id},
                ConditionExpression='attribute_exists(user_id)'  # user_id가 존재할 때만 삭제
            )
        except ClientError as e:
            print(f"Error removing active session: {e}")
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

    def get_current_session_metadata_by_user_id(self, user_id: str, limit: int) -> List[SessionMetadata]:
        """사용자 ID로 세션 메타데이터 조회"""
        try:
            response = self.session_metadata_table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                Limit=limit,
                ScanIndexForward=False  # 최신 세션이 먼저 오도록 정렬
            )
            return [SessionMetadata(**item) for item in response.get('Items', [])]
        except ClientError as e:
            print(f"Error getting sessions for user {user_id}: {e}")
            raise

    def put_message(self, message: Message) -> None:
        """메시지 저장"""
        try:
            self.message_table.put_item(Item=message.model_dump())
        except ClientError as e:
            print(f"Error putting message: {e}")
            raise

    def get_messages_of_user(self, user_id: str, cursor: str, limit: int) -> (List[Message], Optional[str]):
        """세션 ID로 메시지 조회"""
        try:
            query_kwargs = {
                'KeyConditionExpression': Key('user_id').eq(user_id),
                'Limit': limit,
                'ScanIndexForward': False
            }
            if cursor:
                query_kwargs['ExclusiveStartKey'] = {'user_id': user_id, 'sort_key': cursor}

            response = self.message_table.query(**query_kwargs)
            items = response.get('Items', [])
            last_evaluated_key = response.get('LastEvaluatedKey')
            res = [Message(**item) for item in items]
            return res, last_evaluated_key['sort_key'] if last_evaluated_key else None
        except ClientError as e:
            print(f"Error getting messages for session {user_id}: {e}")
            raise
