import json
import boto3
# import openai
from typing import List, Dict, Any
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')

# LangChainSessionTableName = get_parameter('/p-dynamo/DynamoDB/LangChainSessionTableName')
# SessionMetadataTableName = get_parameter('/p-dynamo/DynamoDB/SessionMetadataTableName')
# OpenAIAPIKey = get_parameter('/api-key/openai')

LangChainSessionTableName = "LangChainSession"
SessionMetadataTableName = "SessionMetadata"

langchain_session_table = dynamodb.Table(LangChainSessionTableName)
session_metadata_table = dynamodb.Table(SessionMetadataTableName)

summary_system_prompt = """
You are a helpful assistant that summarizes the conversation.
You will be given a conversation between a user and an AI assistant.
Your Summary will be used after new session for long term memory.
Summarize the conversation in 10 sentences or less.
"""


def get_parameter(name, with_decryption=True):
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(
        Name=name,
        WithDecryption=with_decryption
    )
    return response['Parameter']['Value']


def get_messages_by_session_id(session_id: str) -> List[str]:
    """세션 ID로 메시지 조회"""
    try:
        response = langchain_session_table.get_item(
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


def summarize_messages(messages: List[str]) -> str:
    """OpenAI를 사용한 메시지 요약"""
    # if not messages:
    #     return "요약할 메시지가 없습니다."

    # openai.api_key = OpenAIAPIKey

    # try:
    #     response = openai.ChatCompletion.create(
    #         model="gpt-4o-mini",
    #         messages=[
    #             {"role": "system", "content": summary_system_prompt},
    #             {"role": "user", "content": ''.join(messages)}
    #         ],
    #         temperature=0.3
    #     )

    #     return response.choices[0].message['content'].strip()

    return ''.join(messages)



def update_session_metadata(user_id: str, session_id: str, summary: str, finished_at: int):
    try:
        session_metadata_table.update_item(
            Key={'user_id': user_id, 'session_id': session_id},
            UpdateExpression="SET session_summary = :s, finished_at = :n",
            ExpressionAttributeValues={':s': summary, ':n': finished_at},
        )
    except ClientError as e:
        print(f"Error updating session metadata: {e}")
        raise


def is_valid_old_item(item: Dict[str, Any]) -> bool:
    """유효한 아이템인지 확인"""
    return (
            'user_id' in item and
            'session_id' in item and
            'created_at' in item and
            'expired_at' in item and
            'updated_at' in item
    )


def lambda_handler(event, context):
    for record in event['Records']:
        if record['eventName'] != 'REMOVE':
            continue

        print(record)
        deactivated_session = record['dynamodb'].get('OldImage')

        if not deactivated_session or not is_valid_old_item(deactivated_session):
            continue

        user_id = deactivated_session['user_id']['S']
        session_id = deactivated_session['session_id']['S']
        updated_at = deactivated_session['updated_at']['N']

        messages = get_messages_by_session_id(session_id)
        summary = summarize_messages(messages)
        update_session_metadata(user_id, session_id, summary, updated_at)

    return {
        'statusCode': 200,
        'body': json.dumps('summary succeed')
    }
