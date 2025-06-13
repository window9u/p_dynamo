import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict  # pydantic v2+

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    AWS_REGION: str = "ap-northeast-2"  # 기본값, .env 파일에서 오버라이드 가능
    DYNAMODB_CHAT_MESSAGES_TABLE: str = "ChatMessages"
    DYNAMODB_SESSION_METADATA_TABLE: str = "SessionMetadata"
    DYNAMODB_ACTIVE_SESSION_TABLE: str = "ActiveSession"
    DYNAMODB_LANGCHAIN_TABLE: str = "LangChainSessionTable"
    OPENAI_API_KEY: str = ""  # .env 파일에서 오버라이드 가능

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("Settings loaded from environment and .env file.")
        logger.debug(f"Settings: {self.model_dump()}")  # 민감한 정보 로깅에 주의


settings = Settings()
