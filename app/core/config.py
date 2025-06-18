import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict  # pydantic v2+

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    AWS_REGION: str = "ap-northeast-2"  # 기본값, .env 파일에서 오버라이드 가능
    DYNAMODB_SESSION_METADATA_TABLE: str = "SessionMetadata"
    DYNAMODB_MESSAGE_TABLE: str = "Message"
    DYNAMODB_ACTIVE_SESSION_TABLE: str = "ActiveSession"
    DYNAMODB_LANGCHAIN_TABLE: str = "LangChainSession"
    ACTIVE_SESSION_TTL_SECONDS: int = 10  # 활성 세션 TTL, .env 파일에서 오버라이드 가능
    SESSION_SUMMARY_WINDOW: int = 2
    GET_MESSAGE_HISTORY_WINDOW: int = 10
    TOKEN_LIMIT_PER_SESSION: int = 200  # 세션당 토큰 제한, .env 파일에서 오버라이드 가능
    OPENAI_API_KEY: str = ""  # .env 파일에서 오버라이드 가능

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("Settings loaded from environment and .env file.")
        logger.debug(f"Settings: {self.model_dump()}")  # 민감한 정보 로깅에 주의


settings = Settings()
