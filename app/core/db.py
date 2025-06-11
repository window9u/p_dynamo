import boto3
from app.core.config import settings

def get_dynamodb_resource():
    """DynamoDB 리소스 객체 반환"""
    return boto3.resource('dynamodb', region_name=settings.AWS_REGION)

def get_dynamodb_client():
    """DynamoDB 클라이언트 객체 반환"""
    return boto3.client('dynamodb', region_name=settings.AWS_REGION)