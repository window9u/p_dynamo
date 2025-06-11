import os
from pydantic_settings import BaseSettings, SettingsConfigDict # pydantic v2+

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    AWS_REGION: str = "ap-northeast-2" # 기본값, .env 파일에서 오버라이드 가능
    DYNAMODB_CHAT_MESSAGES_TABLE: str = "ChatMessages"
    DYNAMODB_SESSION_METADATA_TABLE: str = "SessionMetadata"
    DYNAMODB_ACTIVE_SESSION_TABLE: str = "ActiveSession"

settings = Settings()