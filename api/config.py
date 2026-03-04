"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # deepseek
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # douyin device
    douyin_device_id: str = ""

    # redis
    redis_url: str = "redis://localhost:6379"

    # server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    port: int = 8000  # Railway sets PORT env var

    # translation
    translation_cache_ttl: int = 3600

    # rate limiting
    rate_limit_rpm: int = 120

    # logging
    log_level: str = "info"

    # optional proxy for douyin API
    proxy_url: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
