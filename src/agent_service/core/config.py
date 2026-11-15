"""应用配置，基于 pydantic-settings，支持 .env 与环境变量注入。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项，优先级：环境变量 > .env > 默认值。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # LLM（M2 接入后生效）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"


@lru_cache
def get_settings() -> Settings:
    """返回全局 Settings 单例。"""
    return Settings()
